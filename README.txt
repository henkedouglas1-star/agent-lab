AGENT LAB SEO FOUNDATION — OCTOBER 20 2026

Prepared against main branch containing 25 published guides.

FILES
  sitemap.xml: 30 URLs, 25 guides + 5 core pages; no guessed timestamps
  robots.txt: allow public crawling, point crawlers to sitemap

ONE-TIME DEPLOYMENT
1. Upload sitemap.xml and robots.txt to the ROOT of GitHub repo henkedouglas1-star/agent-lab, replacing existing robots.txt.
2. Commit to main after verifying file names and contents.
3. Confirm https://agent-lab-sage.vercel.app/sitemap.xml opens with XML and https://agent-lab-sage.vercel.app/robots.txt references it.
4. Claim https://agent-lab-sage.vercel.app/ as a URL-prefix property in Google Search Console, verify ownership, and submit sitemap.xml.

IMPORTANT
This sitemap is a snapshot. Each approved new guide needs an updated sitemap.
The long-term fix is to update scripts/build.py and milo_os.py together so that sitemap changes stay within Milo's allowed generated files and are included in approved draft PRs. Do not patch scripts/build.py by itself: Milo's safe list forbids extra changed files.
Sitemaps help discovery; they do not guarantee indexing, rankings or visits.
