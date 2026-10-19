# Install Milo v2 in Agent Lab

Milo v2 is a **separate, manual-run workflow**. It leaves Milo v1, the public website, Turnstile, and Resend unchanged.

1. Download and extract `Milo-v2-Agent-Lab.zip`.
2. Open the repository root: https://github.com/henkedouglas1-star/agent-lab/upload/main
3. Upload **only `milo_v2.py`** from the ZIP into the repo root and commit. Check the final path is `milo_v2.py`, not `milo-v2/milo_v2.py`.
4. Open https://github.com/henkedouglas1-star/agent-lab/new/main and set the new file name to **`.github/workflows/milo-v2.yml`**.
5. Paste the **entire contents** of the included `milo-v2.yml` into the editor and commit.
6. Open https://github.com/henkedouglas1-star/agent-lab/actions, select **Milo v2 — Source-screened article drafts**, then Run workflow.
7. Read its result at https://github.com/henkedouglas1-star/agent-lab/issues . A successful run creates an issue titled `Milo v2 article draft | YYYY-MM-DD`.

## What you get

- A grounded research pass for new AI use cases (Google Search tool via Gemini).
- A second draft-writing pass that produces a step-by-step article for human review.
- Basic deterministic checks for source leads, correct source numbering, structure and word count. No GitHub issue is created if these checks fail.
- A transparent audit explaining that source leads are **not** independent fact-checking.
- No autonomous website publishing, sponsor messaging, billing, or automatic daily schedule.

## Required secret

The repository already uses `GEMINI_API_KEY` from GitHub Actions secrets. You do not need a new API key. Existing GitHub Actions token permissions are declared in the workflow.

## Cost and privacy

One manual run makes **two Gemini API requests** (one with Google Search grounding). Gemini and grounding requests may have usage charges. The report is saved as a public GitHub issue because Agent Lab's repository is public. Do not place secrets, private customer data, or confidential research in a Milo prompt.

## Troubleshooting

- No new issue? See the workflow's Actions logs. A failed run leaves the public website untouched.
- No grounding source leads? Milo deliberately stops rather than making an unsupported draft.
- `404` or missing file? Verify that `milo_v2.py` is in the repository root and that the workflow is located at `.github/workflows/milo-v2.yml`.
- If a previous draft exists for the current UTC date, Milo won't create a duplicate.
- Keep `milo-v1.yml` intact until you are happy with v2.
