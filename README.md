# Agent Lab

A complete, framework-free starter site for an AI use-case directory, free educational guides, community roadmap, and sponsorship monetization. Built as static HTML/CSS/JavaScript plus one optional Vercel Node API route.

## Included

- Home page with category collections and featured guides
- **24 prewritten, individually addressable guide pages**, each with implementation steps, a caution, and a link to primary tool documentation
- Searchable directory with category/difficulty filters, URL-based shareable search, and browser-local saved guides
- Sponsorship page with transparent founding-pilot offers and email inquiry form
- Community roadmap page and topic submission form. **No forum backend exists yet**. No fake user posts.
- About page with clear editorial/affiliate/sponsorship disclosure standards
- Sitemap-friendly clean URLs; accessible responsive navigation; no paid frontend dependencies
- `api/inquiry.js` Vercel serverless email delivery through Resend (requires environment variables)

## Run locally

From the project directory:

```bash
python3 -m http.server 8080
```

Open http://localhost:8080/ . The directory, all guides, bookmarking, and page navigation work locally. **Submission forms will not deliver locally**, because the Vercel API function requires deployment and Resend configuration.

## Deploy to Vercel

1. Extract the ZIP into a new Git repository or local project folder (the **entire project root**, not a nested subfolder).
2. From the Vercel dashboard, import the repository. Choose **Other** for framework, leave Build Command empty, and Output Directory empty (serve static files from the project root).
3. Deploy. Pages are immediately usable without any secrets.
4. In Vercel Project Settings → Environment Variables, configure:
   - `RESEND_API_KEY`: Resend API key managed privately in Vercel
   - `INQUIRY_TO_EMAIL`: your private receiving mailbox
   - `INQUIRY_FROM_EMAIL`: an address on a domain verified with Resend, e.g. `Agent Lab <inquiries@your-domain.example>`
5. Redeploy after adding environment variables. Test an inquiry and verify it appears in your mailbox before publicizing sponsorship forms.

**Do not paste any API keys into this project or public chat.** Add them directly in Vercel.

## Maintain content

All guide data is in `data/use_cases.json`. Edit records and run:

```bash
python3 scripts/build.py
```

The script validates slugs, required fields, and source URLs then regenerates static pages. Commit the updated JSON **and** generated HTML. Use editorial approval and verify source links before publishing new AI claims.

## Important limitations and next product milestones

- This package **does not create a public website URL** by itself. You must deploy it through a host.
- The serverless form is **not operational until the Resend environment variables are configured**. Unconfigured forms report an explicit error rather than pretending to send.
- The sponsor offers are **inquiry-based**, not an automatic payment checkout. No charge is initiated.
- Bookmarks use **each visitor's local browser storage**, not an account backend. Clearing storage erases bookmarks.
- The Community page is a prelaunch area. To offer genuine threads, voting, profiles, moderation, abuse handling, and durable submissions, add authentication plus a database. Do not claim community features are live until tested.
- No automatic content publication, persistent analytics, CRM, sponsor billing, or agent CEO has been deployed. Build these after the MVP is public and users are interacting.
- The API has a honeypot and *best-effort instance-local throttling*. Add distributed rate limiting / WAF and bot protection before heavily promoting public forms.
- Search-engine optimization: after assigning a domain, generate a `sitemap.xml` with correct absolute URLs and add canonical tags. Never ship placeholder URLs as production canonicals.

## Suggested simple evolution

1. **Launch**: public URL, verify mobile pages, working inquiry email, analytics, and real source links.
2. **Monetization**: sell first pilot placement via direct outreach to relevant AI product makers, with clear sponsor labeling. Record inquiries, contracts, and outcomes.
3. **Retention**: weekly hand-reviewed case studies, optional email digest, more guides based on measured search demand.
4. **Community**: only add profiles/discussions after moderation, reporting, and anti-spam capabilities can be supported.
5. **AI agent pipeline**: research new ideas → draft entries with source URLs → validate for hype/inaccuracies → human approval → commit and deploy → analyze analytics → repeat. Never permit blind autonomous publishing into public pages.

## Important independent editorial note

AI tool capabilities can change. The source links describe the relevant vendor tools; workflow steps are Agent Lab editorial suggestions, not empirical claims of guaranteed ROI or endorsements by these vendors. All setup-time ranges are approximate estimates.
