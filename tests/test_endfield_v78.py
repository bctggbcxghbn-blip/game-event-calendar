import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'games'/'endfield'))
import diagnose_v78 as m

class TestV78(unittest.TestCase):
    def test_link_and_article_extraction(self):
        p={'url':m.URLS[0],'final_url':m.URLS[0],'http_status':200,'content_type':'text/html','bytes_read':70,'error':None,
           'body':'<a href="/ja-jp/news/12345">news</a><a href="/ja-jp/news/12345">duplicate</a>'}
        d=m.summarize(p)
        self.assertEqual(d['html_anchor_count'],2)
        self.assertEqual(d['unique_anchor_count'],1)
        self.assertEqual(d['new_article_count'],1)
    def test_error_source_is_recorded(self):
        def fake(url):
            return {'url':url,'final_url':url,'http_status':403,'content_type':'','bytes_read':0,'body':'','error':'HTTP Error 403'}
        r=m.run(fake)
        self.assertTrue(r['discovery_warning'])
        self.assertEqual([s['http_status'] for s in r['sources']],[403,403,403])
        self.assertEqual(r['events_added'],0)
    def test_discover_from_sitemap(self):
        def fake(url):
            body='<loc>https://endfield.gryphline.com/ja-jp/news/98765</loc>' if url.endswith('sitemap.xml') else ''
            return {'url':url,'final_url':url,'http_status':200,'content_type':'text/xml','bytes_read':len(body),'body':body,'error':None}
        r=m.run(fake)
        self.assertEqual(r['articles_discovered'],2)
        self.assertFalse(r['discovery_warning'])
        self.assertFalse(r['events_json_changed'])
if __name__=='__main__': unittest.main()
