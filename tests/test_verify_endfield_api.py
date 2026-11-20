import datetime as dt
import unittest

from tools.verify_endfield_api import API_BASE, audit


def listing(rows):
    return {'ok': True, 'status': 200, 'bytes': 100, 'final_url': API_BASE,
            'payload': {'data': {'list': rows}}}


class EndfieldApiAuditTests(unittest.TestCase):
    def test_normal_response_and_deduplication(self):
        calls = {}
        def fetch(url):
            calls[url] = calls.get(url, 0) + 1
            if '/bulletin?' in url:
                return listing([{'cid': '9560'}, {'cid': '9560'}, {'cid': 'bad'}])
            return {'ok': True, 'status': 200, 'bytes': 50,
                    'payload': {'title': '日本語 Ver.1.2.3 Asia 2026/11/01'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        self.assertEqual(report['article_ids'], ['9560'])
        self.assertEqual(report['body_verification_successes'], 1)
        self.assertEqual(report['exclusions']['invalid_cid'], 1)

    def test_empty_and_schema_change_are_unverified(self):
        for payload in ({'data': {'list': []}}, {'data': {'items': []}}):
            report = audit(fetcher=lambda _url, p=payload: {'ok': True, 'status': 200, 'bytes': 1, 'payload': p})
            self.assertEqual(report['candidates'], [])
            self.assertEqual(report['status'], 'unverified')

    def test_detail_failure_future_region_and_missing_body_are_rejected(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '1'}, {'cid': '2'}, {'cid': '3'}])
            cid = url.split('/bulletin/')[1].split('?')[0]
            if cid == '1':
                return {'ok': False, 'status': 504, 'bytes': 0, 'reason': 'TimeoutError'}
            if cid == '2':
                return {'ok': True, 'status': 200, 'bytes': 20, 'payload': {'text': '日本語 Ver.1.2.4 2099/01/01'}}
            return {'ok': True, 'status': 200, 'bytes': 20, 'payload': {'text': 'English Ver.1.2.3 2026/01/01'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        self.assertEqual(report['candidates'], [])
        self.assertEqual(report['exclusions']['detail_failed'], 1)

    def test_listing_failure_preserves_existing_by_not_producing_candidates(self):
        report = audit(fetcher=lambda _url: {'ok': False, 'status': 500, 'bytes': 0, 'reason': 'HTTPError'})
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['candidates'], [])

    def test_only_https_api_host_is_accepted(self):
        from tools.verify_endfield_api import _request
        self.assertEqual(_request('http://web-news.gryphline.com/api/bulletin')['reason'], 'unsafe_url')
        self.assertEqual(_request('https://example.com/api/bulletin')['reason'], 'unsafe_url')


if __name__ == '__main__':
    unittest.main()
