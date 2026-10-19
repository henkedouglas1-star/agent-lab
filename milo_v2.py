#!/usr/bin/env python3
"""Milo v2: research, source-screen, and draft an Agent Lab guide for human review.

GitHub Actions creates a review-only issue. The site is NOT modified and no mail is sent.
The grounded web results are *leads* rather than independently verified evidence.
No external dependencies beyond Python 3.12 standard library.
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GITHUB_API = "https://api.github.com"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
ISSUE_PREFIX = "Milo v2 article draft"
SOURCE_LIMIT = 12
MAX_RESPONSE_BYTES = 300000


def request_json(url, *, method="GET", payload=None, headers=None, timeout=90):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            **(headers or {}),
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("API response exceeded the size limit")
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never log request bodies, headers, or provider responses; API keys are secret.
        raise RuntimeError(f"{urllib.parse.urlsplit(url).hostname} returned HTTP {exc.code}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network request failed ({type(exc.reason).__name__})") from None


def github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Accept": "application/vnd.github+json",
    }


def catalog():
    data = json.loads((ROOT / "data" / "use_cases.json").read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise RuntimeError("Existing Agent Lab catalog was missing or invalid")
    titles = [str(item["title"]) for item in data if item.get("title")]
    categories = sorted(set(str(item["category"]) for item in data if item.get("category")))
    return titles, categories


def valid_grounding_uri(url):
    """Accept web HTTPS citations, never internal/local targets or credentialed URLs.

    We do NOT open these URLs programmatically: Google often returns grounding
    redirects and an HTTP response alone would not establish factual support.
    """
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 32 for c in url):
        return False
    try:
        p = urllib.parse.urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            return False
        hostname = p.hostname.rstrip(".").lower()
        if hostname == "localhost" or hostname.endswith((".local", ".internal", ".test")):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_global
        except ValueError:
            return "." in hostname
    except ValueError:
        return False


def extract_sources(candidate):
    meta = candidate.get("groundingMetadata") or {}
    sources = []
    seen = set()
    for chunk in meta.get("groundingChunks") or []:
        web = chunk.get("web") or {}
        url = web.get("uri")
        if valid_grounding_uri(url) and url not in seen:
            title = re.sub(r"[\[\]\r\n]", "", str(web.get("title") or "Web source"))[:130]
            seen.add(url)
            sources.append((title, url))
    supports = meta.get("groundingSupports") or []
    referenced_indexes = set()
    for support in supports:
        for idx in support.get("groundingChunkIndices") or []:
            if isinstance(idx, int) and idx >= 0:
                referenced_indexes.add(idx)
    return sources[:SOURCE_LIMIT], len(supports), len(referenced_indexes)


def gemini_generate(api_key, model, prompt, *, grounded, max_tokens):
    safe_model = urllib.parse.quote(model, safe="-_.")
    result = request_json(
        f"{GEMINI_BASE}/{safe_model}:generateContent",
        method="POST",
        headers={"x-goog-api-key": api_key},
        payload={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            **({"tools": [{"google_search": {}}]} if grounded else {}),
            "generationConfig": {"temperature": 0.15, "maxOutputTokens": max_tokens},
        },
        timeout=100,
    )
    choices = result.get("candidates") or []
    if not choices:
        raise RuntimeError("Gemini did not return a candidate; check model and quota")
    candidate = choices[0]
    text = "\n".join(
        part.get("text", "") for part in (candidate.get("content") or {}).get("parts", [])
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if len(text) < 250:
        raise RuntimeError("Gemini returned too little text for a useful result")
    return text, candidate


def research_prompt(titles, categories, today):
    existing = "\n".join(f"- {title}" for title in titles[:120])
    return f"""You are Milo, the RESEARCH agent for Agent Lab, a new and small AI-use-case educational site.
Date: {today}. Use Google Search grounding to research NEW, practical AI use cases with primary vendor documentation, not news hype.

Existing guide titles (do not duplicate):
{existing}
Categories: {', '.join(categories)}

Write under 900 words of plain Markdown, using EXACTLY these headings:
## Three candidate workflows
For up to 3 distinctly useful workflows describe audience, practical steps, differentiator vs existing topics, and potential primary source.
## Selected workflow
Select ONE modest and testable idea with a clear target user, scope, actual tools, and why it is achievable.
## Evidence and unknowns
Separate what you can point to in documentation from assumptions, hypotheses and unknowns. Avoid numerical outcome claims unless supported by a published real measurement, and still request an independent check.
## Draft sponsorship fit
Name up to 3 possible vendors by product fit only. No claims of relationships, contact details, audience metrics or any sponsor commitment.

Rules: no fabricated personal experiments, revenue or view numbers, percentages, guarantees, case studies, prices, endorsements, or customer demand. Clearly say the article will be a draft, not verified advice. No URLs invented from memory. Prefer vendor docs over aggregators. Do not imply Agent Lab has an active discussion forum or readership statistics."""


def draft_prompt(research, sources, today):
    source_text = "\n".join(f"{i}. {title}: {url}" for i, (title, url) in enumerate(sources, 1))
    return f"""You are the careful guide writer for Agent Lab. Date: {today}.

Create a complete practical guide draft, 650-1050 words, from the research notes below.
Your output is a public GitHub DRAFT awaiting editor verification, NOT approved to publish.

Research notes (not independently verified):
{research[:8500]}

Search-generated source leads (NOT verified):
{source_text}

Use exactly these headings, each with substantial useful information:
# [Specific, search-friendly how-to title]
## Who this is for
## What you'll build
## What you need
## Step-by-step setup
## How to test it
## Privacy, costs, and failure modes
## Claims requiring editor verification

Rules:
- Describe ONE implementable AI workflow with concrete tests and manual safeguards.
- Use numbered setup instructions for nontechnical readers where possible.
- Do not fabricate prices, dates of feature launches, customer outcomes, performance gains, firsthand tests, business partnerships or audience numbers.
- Never claim any tool or feature is verified just because a source lead exists.
- Don't invent links. For citations inside the draft, ONLY use exact reference tokens [SOURCE 1], [SOURCE 2], etc. There are {len(sources)} provided sources.
- If unsure, write 'Verify in current vendor documentation' instead of guessing.
- Where real user data is involved, specify privacy controls, consent, and human oversight.
- Identify at least three concrete claims or compatibility details the site owner should verify before publishing.
- This is informative content only, not a promise of earnings."""


def check_draft(draft, sources):
    required = [
        "## Who this is for", "## What you'll build", "## What you need",
        "## Step-by-step setup", "## How to test it", "## Privacy, costs, and failure modes",
        "## Claims requiring editor verification",
    ]
    missing = [head for head in required if head not in draft]
    if missing:
        raise RuntimeError("Draft failed structure checks: " + ", ".join(missing))
    word_count = len(draft.split())
    if not 420 <= word_count <= 1500:
        raise RuntimeError(f"Draft failed length check: {word_count} words")
    used_sources = re.findall(r"\[SOURCE\s+(\d+)\]", draft, flags=re.I)
    if any(int(n) < 1 or int(n) > len(sources) for n in used_sources):
        raise RuntimeError("Draft contains a source reference not in the research citations")
    if re.search(r"(?i)\b(?:guaranteed (?:income|profit|results)|(?:increase|improve|reduce|save)[^\n.!?]{0,50}\bby\s+\d+\s*%)", draft):
        raise RuntimeError("Draft contains an unsupported quantitative or guaranteed outcome claim")
    return word_count, len(set(used_sources))


def safe_source_link(title, url):
    # Markdown-safe title and URL from Google's grounding metadata, not model-written URLs.
    display = re.sub(r"[\[\]<>\r\n]", "", title).replace("|", " ")
    return f"[{display}]({url.replace(')', '%29').replace('(', '%28')})"


def issue_body(today, research, draft, sources, support_count, referenced_count, model, word_count, linked_count):
    catalog_refs = "\n".join(f"{i}. {safe_source_link(title, url)}" for i, (title, url) in enumerate(sources, 1))
    # Prevent accidental GitHub cross-issue pings or owner mentions in model-generated material.
    def suppress_mentions(text):
        return re.sub(r"(?<!\w)@(?=[A-Za-z0-9])", "@\u200b", text)
    return suppress_mentions(f"""# Milo v2: source-screened guide draft — {today}

**Status:** EDITOR REVIEW REQUIRED · **Model:** `{model}` · **Not published on Agent Lab**

> This draft is NOT independently fact-checked. The Google Search grounding metadata supplies **source leads**, not proof for every claim. Do not publish until you review the primary documents and run a small workflow test.
>
> No website changes, sponsor outreach, purchase, or emails were performed.

## Automatic checks
- At least 2 distinct HTTPS grounding source leads: **PASS ({len(sources)})**
- Grounding support segments reported: **{support_count}** (source references in support metadata: {referenced_count}; informational only)
- Draft structure and length: **PASS ({word_count} words)**
- Draft references to numbered source leads: **{linked_count} distinct**
- Independent factual verification / current product availability: **NOT DONE**

---

## Suggested article — draft only

{draft}

---

## Research reasoning — unverified

{research}

## Grounded search source leads
{catalog_refs}

## Owner approval checklist
- [ ] Open and read primary vendor documentation; replace redirect URLs with canonical sources where possible
- [ ] Check each technical capability, setup screen, price, and compatibility claim
- [ ] Test the workflow yourself before promising any measurable result
- [ ] Review wording for originality, privacy, accessibility, and safe defaults
- [ ] Confirm guide doesn't duplicate an existing Agent Lab guide
- [ ] Only then approve a separate publish action; this issue does not publish anything
""")


def run():
    api_key = os.getenv("GEMINI_API_KEY", "")
    gh_token = os.getenv("GITHUB_TOKEN", "")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    model = os.getenv("MILO_GEMINI_MODEL", DEFAULT_MODEL)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing: add it under GitHub Actions repository secrets")
    if not gh_token or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise RuntimeError("Run from GitHub Actions with GITHUB_TOKEN and GITHUB_REPOSITORY")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    title = f"{ISSUE_PREFIX} | {today}"
    issues_api = f"{GITHUB_API}/repos/{repo}/issues"
    # Include already-closed issues: rerunning on a day won't create duplicate public drafts.
    issues = request_json(issues_api + "?state=all&per_page=100", headers=github_headers(gh_token))
    if any(isinstance(issue, dict) and issue.get("title") == title for issue in issues):
        print(f"Today's Milo v2 draft already exists: {title}. No duplicate created.")
        return

    titles, categories = catalog()
    print(f"Milo v2 screening a new guide against {len(titles)} existing guides")
    research, research_candidate = gemini_generate(api_key, model, research_prompt(titles, categories, today), grounded=True, max_tokens=3000)
    sources, support_count, referenced_count = extract_sources(research_candidate)
    # Fail closed rather than publish misleading research as 'verified'.
    if len(sources) < 2:
        raise RuntimeError(f"Grounded research supplied {len(sources)} usable source leads; at least 2 required. No draft issue created.")

    draft, _ = gemini_generate(api_key, model, draft_prompt(research, sources, today), grounded=False, max_tokens=4000)
    words, cited = check_draft(draft, sources)
    response = request_json(
        issues_api,
        method="POST",
        headers=github_headers(gh_token),
        payload={"title": title, "body": issue_body(today, research, draft, sources, support_count, referenced_count, model, words, cited)},
    )
    print(f"Milo v2 created review-only draft: {response.get('html_url', '(unavailable)')}")
    print(f"Evidence: {len(sources)} search leads, {support_count} grounding support segments. Independent verification still required.")


if __name__ == "__main__":
    try:
        run()
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        print(f"Milo v2 failed safely: {exc}", file=sys.stderr)
        sys.exit(1)
