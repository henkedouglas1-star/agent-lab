#!/usr/bin/env python3
"""Offline publication gate; structural checks are not integration testing."""
import argparse, json, pathlib, re, subprocess, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET
ROOT = pathlib.Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.ids=set(); self.h1=0; self.title=0; self.descriptions=[]; self.canonicals=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get('id'): self.ids.add(a['id'])
        if tag=='h1': self.h1+=1
        if tag=='title': self.title+=1
        if tag=='meta' and a.get('name')=='description': self.descriptions.append(a.get('content',''))
        if tag=='link' and a.get('rel')=='canonical': self.canonicals.append(a.get('href'))
        for key in ('href','src'):
            if a.get(key): self.links.append(a[key])
def validate(base_ref=None):
    items=json.loads((ROOT/'data/use_cases.json').read_text()); errors=[]
    slugs=[x['slug'] for x in items]
    if len(slugs)!=len(set(slugs)): errors.append('Duplicate guide slug')
    titles=[re.sub(r'[^a-z0-9]+',' ',x['title'].lower()).strip() for x in items]
    if len(titles)!=len(set(titles)): errors.append('Duplicate normalized article title')
    if base_ref:
        # Browser uploads can preserve base content without a merge commit.
        # Pin the reviewed main snapshot; fail after any newer main commit.
        snapshot=(ROOT/'editorial-base.txt').read_text().strip()
        current=subprocess.check_output(['git','rev-parse',base_ref],cwd=ROOT,text=True).strip()
        if snapshot!=current:
            errors.append('Reviewed main snapshot is stale: incorporate current main and regenerate')
        old=json.loads(subprocess.check_output(['git','show',base_ref+':data/use_cases.json'],cwd=ROOT,text=True))
        if not {x['slug'] for x in old}<=set(slugs): errors.append('Approved base guide removed')
        by_slug={x['slug']:x for x in items}
        if any(by_slug.get(x['slug'])!=x for x in old): errors.append('Approved base content changed; explicit editorial review required')
    pages={}
    for f in ROOT.rglob('*.html'):
        if '.git' in f.parts: continue
        p=Page(); p.feed(f.read_text()); pages[f.resolve()]=p
    expected={'/','/directory/','/community/','/about/','/sponsor/'}|{'/guides/'+s+'/' for s in slugs}
    urls=[n.text for n in ET.parse(ROOT/'sitemap.xml').iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    if len(urls)!=len(set(urls)) or set(urls)!={'https://agent-lab-sage.vercel.app'+p for p in expected}: errors.append('Sitemap does not exactly match catalog and core pages')
    for x in items:
        f=(ROOT/'guides'/x['slug']/'index.html').resolve(); p=pages.get(f)
        if not p: errors.append('Missing guide '+x['slug']); continue
        if p.h1!=1 or p.title!=1 or len(p.descriptions)!=1 or not p.descriptions[0]: errors.append('Invalid guide SEO structure '+x['slug'])
        if x.get('tutorial'):
            t=x['tutorial']
            if not all(t.get(k) for k in ('prompt','sample_input','expected_output','tests','notes','sources')): errors.append('Incomplete implementation tutorial '+x['slug'])
            if not any(re.search(r'ambiguous|ignore|missing|refund',v['input'],re.I) for v in t['tests']): errors.append('Missing failure test '+x['slug'])
            if p.canonicals!=['https://agent-lab-sage.vercel.app/guides/'+x['slug']+'/']: errors.append('Incorrect canonical '+x['slug'])
            if any(not s['url'].startswith('https://') for s in t['sources']): errors.append('Invalid documentation URL')
    for f,p in pages.items():
        for href in p.links:
            u=urlsplit(href)
            if u.scheme or u.netloc: continue
            target=(ROOT/unquote(u.path).lstrip('/') if u.path.startswith('/') else f.parent/unquote(u.path)) if u.path else f
            if target.is_dir(): target=target/'index.html'
            target=target.resolve()
            if not target.is_file(): errors.append('Broken link '+str(f.relative_to(ROOT))+': '+href)
            elif u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids: errors.append('Missing anchor '+href)
    directory=(ROOT/'directory/index.html').read_text(); home=(ROOT/'index.html').read_text()
    if directory.count('data-card data-id=')!=len(items) or f'Search {len(items)} practical guides' not in directory or f'Explore {len(items)} AI use cases' not in home: errors.append('Incorrect guide counts')
    if errors:
        for error in errors: print('FAIL:',error)
        return 1
    print(f'PASS: {len(items)} catalog guides; {len(pages)} HTML pages; {len(urls)} sitemap URLs; internal links, anchors, counts and guide SEO structure. No Zapier integrations executed.')
    return 0
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--base-ref'); args=parser.parse_args(); sys.exit(validate(args.base_ref))
