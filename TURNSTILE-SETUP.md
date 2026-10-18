# Agent Lab Turnstile protection

This security update changes the sponsorship and community inquiry forms, and preserves the current Resend email integration.

## Before deploying

1. Create a Cloudflare Turnstile widget with hostname `agent-lab-sage.vercel.app` and mode **Managed**.
2. Add Vercel **Production** environment variables `TURNSTILE_SITE_KEY` (public sitekey) and `TURNSTILE_SECRET_KEY` (secret; set Sensitive). Keep all three existing Resend variables unchanged.
3. Upload `api/inquiry.js`, `api/turnstile-config.js`, and `assets/app.js` from this patch into the same paths in the GitHub repository, commit changes, then allow Vercel to deploy.

## Verification

- `https://agent-lab-sage.vercel.app/api/turnstile-config` should return JSON containing `siteKey`, not a secret.
- On `/sponsor/`, the Turnstile widget appears near the Send button.
- Incomplete challenge => cannot send.
- Valid challenge => Resend accepts inquiry; verify the actual inquiry arrives.
- A reused/expired token => server rejects it.
- No success message is returned by the old honeypot code.
- Check `/community/` similarly.

**Note:** Vercel's `TURNSTILE_SITE_KEY` is exposed intentionally to the browser through a minimal API. `TURNSTILE_SECRET_KEY` is never exposed. Do not commit the secret or keys in source files.
