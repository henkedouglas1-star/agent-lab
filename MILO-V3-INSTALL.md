# Milo v3 for Agent Lab — installation

This version runs in **review-only mode**. It never publishes to the website, contacts sponsors, sends emails or makes purchases. Milo v1/v2 and the existing site remain unchanged.

## Files

- `milo_v3.py` → GitHub repository **root** (`/milo_v3.py`)
- `milo-v3.yml` → `.github/workflows/milo-v3.yml` (NOT the repository root)

## Installation

1. Open https://github.com/henkedouglas1-star/agent-lab/upload/main and upload the **file** `milo_v3.py`. Commit to `main`.
2. Open https://github.com/henkedouglas1-star/agent-lab/tree/main/.github/workflows, select **Add file → Upload files**, and upload `milo-v3.yml` to that workflow folder. Commit to `main`.
3. Confirm existing GitHub Actions secret `GEMINI_API_KEY` is configured (used by v1 and v2). No new key is needed.
4. Visit https://github.com/henkedouglas1-star/agent-lab/actions and choose **Milo v3 — Official-doc article review**. Select **Run workflow**, branch `main`, **Run workflow**.
5. Examine the resulting GitHub issue at https://github.com/henkedouglas1-star/agent-lab/issues; expected title begins with **Milo v3 reviewed article draft**.

## Important limitations

- Every result is a **draft**. Source pages are fetched via HTTPS but their claims are NOT independently verified. Read original official docs and run any code sample yourself before approving publication.
- If the model invents unopenable documentation URLs, or vendor docs block automated reading, Milo v3 **stops without creating a misleading article**. This may appear as a red workflow run; inspect the run logs, not your secret value.
- If the format, citations, code syntax, or duplicate checks fail, Milo creates a GitHub issue marked **HOLD** instead of pretending the article is approved.
- Do not upload API keys or tokens into the repository or issues. The existing `GEMINI_API_KEY` Actions secret is used.
- Running Gemini API and Google Search grounding can incur charges according to your Google account and model pricing.
- This workflow is manually triggered only; it is not scheduled.

## Local test

`python -m unittest discover -s tests -v`
