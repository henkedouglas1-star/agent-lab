"""Unit and integration-style tests, with all external requests mocked."""
import importlib.util
import json
import os
import unittest
from unittest.mock import patch
from pathlib import Path

P = Path(__file__).parent/'milo_v3.py'
spec=importlib.util.spec_from_file_location('milo',P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

VALID_DOCS=['https://docs.github.com/en/rest/overview','https://docs.n8n.io/hosting/']
PLAN={'title':'Compile Weekly Release Notes with AI and GitHub',
      'audience':'Release managers','workflow':'Write release notes from commit data',
      'differentiator':'Different from general articles','official_urls':VALID_DOCS}
CANDIDATE={'groundingMetadata':{'groundingChunks':[{'web':{'title':'docs.github.com','uri':'https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc'}}],
                               'groundingSupports':[{'segment':{'text':'example'}}]}}

DRAFT = '''# Compile Weekly Release Notes with AI and GitHub
## Who this helps
Release managers with repeated release work.
## Result and prerequisites
A reviewable weekly draft.
## Step-by-step walkthrough
1. Gather sanitized example commits.
2. Extract change descriptions from the sample.
3. Sort changes by user impact.
4. Draft release notes from known inputs.
5. Compare every claim with its source before using.
## Copy-ready example
```python
records = ["Fix A", "Fix B", "Fix C"]
labels = ["Bug fix", "Bug fix", "Change"]
for record, label in zip(records, labels):
    print(f"{label}: {record}")
print("Review each summary with a person")
```
## Test with sample data
Expected: three lines and a review reminder. Failure test: use an empty input list and confirm empty output.
## Privacy, cost, and limitations
Do not use customer secrets, and verify the API scope and pricing.
## Evidence and claims to check
Review the source reference [LEAD1] before using live production API capabilities.
'''+('This draft makes no claim of tested accuracy. ' * 85)

class MiloTest(unittest.TestCase):
    def test_doc_url_safety(self):
        self.assertTrue(m.safe_doc_url('https://docs.github.com/en/rest'))
        self.assertFalse(m.safe_doc_url('https://evil.example.com/?x=docs.github.com'))
        self.assertFalse(m.safe_doc_url('http://docs.github.com/en/rest'))
        self.assertFalse(m.safe_doc_url('https://docs.github.com:8443/en/rest'))
        self.assertFalse(m.safe_doc_url('https://user:pass@docs.github.com/en/rest'))
    def test_fragment_remove(self):
        self.assertEqual(m.normalized_doc_url(VALID_DOCS[0]+'#foo'),VALID_DOCS[0])
    def test_json_prefix_and_fences(self):
        self.assertEqual(m.json_object('note: '+json.dumps(PLAN)),PLAN)
        self.assertEqual(m.json_object('```json\n'+json.dumps(PLAN)+'\n```'),PLAN)
        with self.assertRaises((ValueError,json.JSONDecodeError)):
            m.json_object('definitely not JSON')
    def test_grounding_source_leads_metadata(self):
        leads, segments=m.grounded_leads(CANDIDATE)
        self.assertEqual((len(leads),segments),(1,1))
        self.assertNotIn('body',leads[0])
    def test_grounding_rejects_unsafe(self):
        out,_=m.grounded_leads({'groundingMetadata':{'groundingChunks':[{'web':{'uri':'http://localhost/private'}},{'web':{'uri':'https://user:pass@example.com/'}}]}})
        self.assertEqual(out,[])
    def test_status_zero_readable(self):
        sources=[{'url':u,'status':'unread','excerpt':''} for u in VALID_DOCS]
        issue=m.create_issue_body('2026-10-19','test-model',PLAN,sources,[],0,DRAFT,[],len(DRAFT.split()),[])
        self.assertIn('HOLD',issue)
        self.assertIn('NO factual support',issue)
    def test_status_two_readable(self):
        sources=[{'url':u,'status':'opened','excerpt':'sample text'} for u in VALID_DOCS]
        issue=m.create_issue_body('2026-10-19','test-model',PLAN,sources,[{'url':'https://a.com','title':'search lead'}],1,DRAFT,[],len(DRAFT.split()),[])
        self.assertIn('EDITOR REVIEW REQUIRED',issue)
        self.assertIn('not independently verified',issue.lower())
    def test_draft_detects_bad_citation(self):
        sources=[{'url':u,'status':'unread','excerpt':''} for u in VALID_DOCS]
        error,words=m.check_draft(DRAFT.replace('[LEAD1]','[DOC1]'),sources,[])
        self.assertTrue(any('Incorrect evidence label' in e for e in error))
    def test_draft_detects_syntax_errors(self):
        sources=[{'url':u,'status':'unread','excerpt':''} for u in VALID_DOCS]
        bad=DRAFT.replace('    print(f"{label}: {record}")','    print(((')
        error,words=m.check_draft(bad,sources,[])
        self.assertTrue(any('syntax error' in e for e in error))
    def test_draft_good_structure(self):
        sources=[{'url':u,'status':'unread','excerpt':''} for u in VALID_DOCS]
        error,words=m.check_draft(DRAFT,sources,[])
        self.assertEqual(error,[])
    def test_prompt_unread_not_evidence(self):
        prompt=m.draft_prompt(PLAN,[{'url':VALID_DOCS[0],'status':'unread','excerpt':''}],[])
        self.assertIn('No page content was read',prompt)
        self.assertIn('Never cite [LEADn] as verified evidence',prompt)
    def test_run_after_blocked_docs_still_creates_article(self):
        created=[]
        def fake_api(url,**kw):
            if kw.get('payload'):
                created.append(kw['payload']);return {'html_url':'https://github.com/fake/issues/1'}
            return []
        def fake_gen(*a,**kw):
            if kw.get('grounded'):
                return (json.dumps(PLAN),CANDIDATE)
            return DRAFT
        with patch.dict(os.environ,{'GEMINI_API_KEY':'dummy','GITHUB_TOKEN':'dummy','GITHUB_REPOSITORY':'example/agent-lab'}), \
             patch.object(m,'request_json',side_effect=fake_api), \
             patch.object(m,'gemini',side_effect=fake_gen), \
             patch.object(m,'catalog',return_value=[{'title':'Plan a user research meeting','summary':'sample'}]), \
             patch.object(m,'fetch_official_excerpt',return_value=None):
            m.run()
        self.assertEqual(len(created),1)
        self.assertIn('Proposed article',created[0]['body'])
        self.assertIn('HOLD',created[0]['body'])
        self.assertEqual(created[0]['title'],'Milo v3.2 article draft | 2026-10-19')
    def test_run_with_two_docs_creates_review_issue(self):
        created=[]
        def fake_api(url,**kw):
            if kw.get('payload'):
                created.append(kw['payload']);return {'html_url':'https://github.com/fake/issues/2'}
            return []
        def fake_gen(*a,**kw):
            if kw.get('grounded'):return(json.dumps(PLAN),CANDIDATE)
            return DRAFT.replace('[LEAD1]','[DOC1]')
        def fake_fetch(url,reasons=None):
            return {'url':url,'excerpt':'Official docs '+('sample doc text ' * 30)}
        with patch.dict(os.environ,{'GEMINI_API_KEY':'dummy','GITHUB_TOKEN':'dummy','GITHUB_REPOSITORY':'example/agent-lab'}), \
             patch.object(m,'request_json',side_effect=fake_api), \
             patch.object(m,'gemini',side_effect=fake_gen), \
             patch.object(m,'catalog',return_value=[{'title':'Plan a user research meeting','summary':'sample'}]), \
             patch.object(m,'fetch_official_excerpt',side_effect=fake_fetch):
            m.run()
        self.assertEqual(len(created),1)
        self.assertIn('EDITOR REVIEW REQUIRED',created[0]['body'])
    def test_no_document_leads_creates_hold_diagnostic(self):
        created=[]
        def fake_api(url,**kw):
            if kw.get('payload'):created.append(kw['payload']);return {'html_url':'https://github.com/fake/issues/3'}
            return []
        def fake_gen(*a,**kw):
            return (json.dumps({**PLAN,'official_urls':['https://not-allowed.example.com']}),CANDIDATE)
        with patch.dict(os.environ,{'GEMINI_API_KEY':'dummy','GITHUB_TOKEN':'dummy','GITHUB_REPOSITORY':'example/agent-lab'}), \
             patch.object(m,'request_json',side_effect=fake_api), \
             patch.object(m,'gemini',side_effect=fake_gen), \
             patch.object(m,'catalog',return_value=[{'title':'Plan a user research meeting','summary':'sample'}]):
            m.run()
        self.assertEqual(len(created),1)
        self.assertIn('NO ARTICLE',created[0]['body'])
if __name__=='__main__':unittest.main(verbosity=2)
