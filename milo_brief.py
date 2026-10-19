#!/usr/bin/env python3
"""Milo v1: generate a review-only Agent Lab research brief in GitHub Issues.

No website publishing, email outreach, or storage of personal information.
Only Python standard library needed. Credentials come from GitHub Actions secrets.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GITHUB_API = "https://api.github.com"
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def api_json(url: str, *, method: str = "GET", payload=None, headers=None, timeout=40):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Accept": "application/json", **(headers or {}), **({"Content-Type": "application/json"} if body else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        # Never print response bodies or request headers: they may contain sensitive data.
        raise RuntimeError(f"{urllib.parse.urlparse(url).hostname} returned HTTP {err.code}") from None
    except urllib.error.URLError as err:
        raise RuntimeError(f"Network request failed: {type(err.reason).__name__}") from None


def load_catalog():
    items = json.loads((ROOT / "data" / "use_cases.json").read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise RuntimeError("Agent Lab use-case catalog is empty or invalid")
    titles = [str(item["title"]) for item in items if "title" in item]
    categories = sorted({str(item["category"]) for item in items if "category" in item})
    return titles, categories


def make_prompt(titles, categories, day):
    catalog = "\n".join(f"- {x}" for x in titles[:120])
    return f"""You are Milo, the proposed AI operations manager for Agent Lab: https://agent-lab-sage.vercel.app/.
Date: {day}. Your output is a RESEARCH DRAFT for the human site owner, not publication-ready material.
Agent Lab helps founders, creators, small businesses and workers discover practical AI use cases.
The public site has a directory, free guides, and sponsor inquiry offers, but no working community forum yet.

Use GOOGLE SEARCH GROUNDING to research CURRENT, specifically useful AI workflows or official tool updates.
Prefer primary documentation and real examples. Search broadly enough for genuine findings.
Never present unsourced market size, revenue numbers, product claims or financial guarantees as facts.
Do not invent clients, contacts, sponsor relationships, website analytics, or the site's readership.
Do not confuse a sponsor prospect with a committed sponsor. Do not email or publish anything.

Avoid repeating existing guide topics. EXISTING GUIDE TITLES:\n{catalog}
EXISTING CATEGORIES: {', '.join(categories)}

Write clear concise Markdown in these sections:
## 1. Today's strongest new AI use cases
Recommend up to 3 ideas. For each: specific audience, practical workflow, why it differs from existing guides, primary source to review, caution.
## 2. Best content draft to prepare next
Select ONE idea. Give a 5-step article outline, a falsifiable practical claim, and what must be tested before publication.
## 3. Sponsorship pipeline
Name at most 3 *potential* relevant vendors or types of tools, only with a grounded reason for fit. Provide a natural human-written outreach angle as an IDEA, not a sent email; do not assume any contacts or consent.
## 4. One concrete next action
Pick one task with the strongest near-term route to useful content, traffic or sponsorship inquiry. Be realistic about what can earn money; no guaranteed outcomes.
## 5. Open questions and confidence
List unverified items and next verification steps.
Keep the whole report under 850 words. If current web grounding fails, clearly say you lack verified sources.
"""


def model_response(api_key, model, prompt):
    safe_model = urllib.parse.quote(model, safe="-_.")
    result = api_json(
        f"{GEMINI_BASE}/{safe_model}:generateContent",
        method="POST",
        headers={"x-goog-api-key": api_key},
        payload={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2500},
        },
        timeout=90,
    )
    candidates = result.get("candidates") or []
    if not candidates:
        raise RuntimeError("AI model returned no candidate (check model availability and quota)")
    candidate = candidates[0]
    text = "\n".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", []) if isinstance(part, dict)).strip()
    if len(text) < 200:
        raise RuntimeError("AI model returned no useful research brief")
    sources = []
    for entry in (candidate.get("groundingMetadata") or {}).get("groundingChunks", []):
        web = entry.get("web") or {}
        uri, title = web.get("uri", ""), web.get("title", "Untitled source")
        if isinstance(uri, str) and uri.startswith("https://") and uri not in [x[1] for x in sources]:
            sources.append((str(title)[:160], uri))
    return text, sources


def issue_markdown(day, report, sources, model):
    refs = "\n".join(f"- [{name.replace('[','').replace(']','')}]({url})" for name, url in sources[:20])
    if not refs:
        refs = "- No machine-provided source links. Treat this report as UNVERIFIED; manually locate authoritative sources."
    return f"""# Milo research and growth brief — {day}

**Status:** Draft for human review · **Model:** `{model}` · **Site:** https://agent-lab-sage.vercel.app/

> Milo has **not** published an article, emailed sponsors, changed site content, or verified every model-generated claim.
> The model's research suggestions and source links require human checking.

{report}

---

## Source leads from the search tool
{refs}

## Owner checklist
- [ ] Check important claims directly against the source pages
- [ ] Decide whether the suggested guide is accurate and distinct from existing content
- [ ] Confirm potential sponsor relevance and any outreach contact independently
- [ ] Approve any actual article or outbound message before it is sent or published
"""


def github_headers(token):
    return {"Authorization": f"Bearer {token}", "X-GitHub-Api-Version": "2022-11-28", "Accept": "application/vnd.github+json"}


def run():
    api_key = os.getenv("GEMINI_API_KEY", "")
    gh_token = os.getenv("GITHUB_TOKEN", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    model = os.getenv("MILO_GEMINI_MODEL", DEFAULT_MODEL)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it under the repository's GitHub Actions secrets.")
    if not gh_token or not repository or repository.count("/") != 1:
        raise RuntimeError("This script must run from GitHub Actions with GITHUB_TOKEN and GITHUB_REPOSITORY.")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    title = f"Milo research brief | {today}"
    uri = f"{GITHUB_API}/repos/{repository}/issues"
    issues = api_json(uri + "?" + urllib.parse.urlencode({"state": "all", "per_page": 100}), headers=github_headers(gh_token))
    if any(isinstance(issue, dict) and issue.get("title") == title for issue in issues):
        print(f"Milo already created today's brief: {title}. No duplicate issue created.")
        return
    titles, cats = load_catalog()
    print(f"Milo evaluating {len(titles)} existing Agent Lab guides using {model}.")
    brief, sources = model_response(api_key, model, make_prompt(titles, cats, today))
    response = api_json(
        uri,
        method="POST",
        headers=github_headers(gh_token),
        payload={"title": title, "body": issue_markdown(today, brief, sources, model)},
    )
    print(f"Created review-only research issue: {response.get('html_url', '(URL unavailable)')}")
    print(f"Search tool supplied {len(sources)} distinct source leads. Manually verify before relying on them.")


if __name__ == "__main__":
    try:
        run()
    except (RuntimeError, KeyError, ValueError, OSError) as exc:
        print(f"Milo error: {exc}", file=sys.stderr)
        sys.exit(1)
