import datetime as dt
import unittest

from tools.verify_endfield_api import API_BASE, audit, _verify_article_identity, _classify_named_version, _extract_named_version


def listing(rows):
    return {'ok': True, 'status': 200, 'bytes': 100, 'final_url': API_BASE,
            'payload': {'data': {'list': rows}}}


def article_html(cid='9560', title='日本語告知', published='2026/01/01'):
    return {'ok': True, 'status': 200, 'bytes': 120,
            'html': f'<html><title>{title}</title><span data-cid="{cid}">{published}</span></html>'}


class EndfieldApiAuditTests(unittest.TestCase):
    def test_normal_response_and_deduplication(self):
        calls = {}
        def fetch(url):
            calls[url] = calls.get(url, 0) + 1
            if '/bulletin?' in url:
                return listing([{'cid': '9560'}, {'cid': '9560'}, {'cid': 'bad'}])
            return {'ok': True, 'status': 200, 'bytes': 50,
                    'payload': {'title': '日本語 Ver.1.2.3 Asia 2026/11/01'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20), article_fetcher=lambda _url: article_html())
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
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20), article_fetcher=lambda url: article_html(url.split('/')[-1]))
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

    def test_article_diagnostics_separate_context_version_and_date(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '10'}, {'cid': '11'}, {'cid': '12'}, {'cid': '13'}])
            cid = url.split('/bulletin/')[1].split('?')[0]
            bodies = {
                '10': {'text': '日本語の告知ですが地域表記なし 2026/01/01'},
                '11': {'text': 'Asia向けですが Ver.1.2.3 の日付なし'},
                '12': {'text': '日本語 Asia Ver.1.2.3 2099/01/01'},
                '13': {'text': '日本語 Asia Ver.1.2.3 2026/01/01'},
            }
            return {'ok': True, 'status': 200, 'bytes': 20, 'payload': bodies[cid]}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        by_id = {row['cid']: row['diagnostics'] for row in report['details']}
        self.assertIn('missing_region_context', by_id['10']['exclusion_reasons'])
        self.assertIn('missing_effective_date', by_id['11']['exclusion_reasons'])
        self.assertIn('future_effective_date', by_id['12']['exclusion_reasons'])
        self.assertEqual(report['body_verification_successes'], 1)
        self.assertEqual(report['exclusion_counts']['future_effective_date'], 1)

    def test_invalid_detail_is_diagnosed_without_body_storage(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '20'}])
            return {'ok': True, 'status': 200, 'bytes': 2, 'payload': None}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        diag = report['details'][0]['diagnostics']
        self.assertIn('invalid_detail_schema', diag['exclusion_reasons'])
        self.assertNotIn('text', diag)

    def test_pagination_collects_pages_and_prioritizes_related_articles(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if '/bulletin/' in url:
                return {'ok': True, 'status': 200, 'bytes': 10, 'payload': {'text': '日本語のお知らせ'}}
            page = int(url.split('page=')[1].split('&')[0])
            if page == 1:
                return listing([{'cid': '1', 'title': '通常のお知らせ', 'displayTime': '2026-11-20'}])
            if page == 2:
                return listing([{'cid': '2', 'title': '丹青渡 バージョンアップデート', 'tab': 'ニュース'}])
            return listing([])
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        self.assertEqual([x['cid'] for x in report['article_inventory']], ['1', '2'])
        self.assertEqual(report['related_articles'][0]['cid'], '2')
        self.assertEqual(report['pages'][-1]['termination'], 'empty_page')
        self.assertEqual(report['article_ids'], ['2', '1'])

    def test_page_error_keeps_previous_page_diagnostics(self):
        def fetch(url):
            if '/bulletin/' in url:
                return {'ok': True, 'status': 200, 'bytes': 10, 'payload': {'text': '日本語のお知らせ'}}
            page = int(url.split('page=')[1].split('&')[0])
            if page == 1:
                return listing([{'cid': '1', 'title': '通常のお知らせ'}])
            return {'ok': False, 'status': 503, 'bytes': 0, 'reason': 'HTTPError'}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        self.assertEqual(report['article_inventory'][0]['cid'], '1')
        self.assertEqual(len(report['pages']), 2)
        self.assertEqual(report['pages'][1]['status'], 503)

    def test_named_version_and_asia_maintenance_are_diagnostic_only(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '9560'}])
            return {'ok': True, 'status': 200, 'bytes': 100, 'payload': {
                'title': '「丹青渡」バージョンアップデートについて',
                'content': '新バージョン「丹青渡」がまもなくリリースされます。'
                           ' Asiaサーバー：2026/10/15 06:00～2026/10/15 12:00（UTC+8）'
            }}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        named = report['details'][0]['diagnostics']['named_version']
        self.assertEqual(named['named_version'], '丹青渡')
        self.assertEqual(named['numeric_version'], None)
        self.assertEqual(named['maintenance_start']['jst'], '2026-10-15T07:00:00+09:00')
        self.assertEqual(named['maintenance_end']['jst'], '2026-10-15T13:00:00+09:00')
        self.assertIsNone(named['effective_from'])
        self.assertFalse(named['accepted_as_current'])

    def test_event_or_scout_name_is_not_named_version(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '1'}])
            return {'ok': True, 'status': 200, 'bytes': 20, 'payload': {
                'title': '特別スカウト「万象一新」', 'content': '日本語 Asia 2026/10/15'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        named = report['details'][0]['diagnostics']['named_version']
        self.assertIsNone(named['named_version'])

    def test_cid_mapping_unverified_is_not_accepted(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '2'}])
            return {'ok': True, 'status': 200, 'bytes': 20, 'payload': {
                'content': '新バージョン「雪氷の幽夢」バージョンアップデート 日本語 Asia 2026/10/15'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20))
        named = report['details'][0]['diagnostics']['named_version']
        self.assertEqual(named['status'], 'unverified_named')
        self.assertFalse(named['cid_url_mapping_verified'])
        self.assertFalse(named['accepted_as_current'])

    def test_http_200_without_identity_match_is_unverified(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '42', 'title': '丹青渡 バージョンアップデート'}])
            return {'ok': True, 'status': 200, 'bytes': 20,
                    'payload': {'title': '日本語 Ver.1.2.3 Asia 2026/01/01'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20),
                       article_fetcher=lambda _url: article_html('999', '別の記事'))
        self.assertFalse(report['url_verification'][0]['verified'])
        self.assertIn('article_url_unverified', report['exclusions'])
        self.assertEqual(report['candidates'], [])

    def test_title_update_is_prioritized_and_cid_match_verifies(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '1', 'title': '通常のお知らせ', 'brief': '新バージョンの案内'},
                                {'cid': '2', 'title': '丹青渡 バージョンアップデート', 'brief': 'メンテナンス'}])
            cid = url.split('/bulletin/')[1].split('?')[0]
            return {'ok': True, 'status': 200, 'bytes': 20,
                    'payload': {'title': '日本語 Ver.1.2.3 Asia 2026/01/01', 'content': '日本語 Asia 2026/01/01'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 20),
                       article_fetcher=lambda url: article_html(url.split('/')[-1]))
        self.assertEqual(report['article_ids'], ['2', '1'])
        self.assertEqual(report['url_verification'][0]['method'], 'cid')
        self.assertEqual(report['priority'][0]['priority'], 'title_update')

    def test_official_article_ids_are_verified_and_mismatches_rejected(self):
        payload = {'cid': '7011', 'articleUrl': 'https://endfield.gryphline.com/ja-jp/news/7011',
                   'title': 'キノコ菌グ！？君との大冒険！', 'displayTime': '2026-11-22'}
        html = {'ok': True, 'status': 200,
                'html': '<title>キノコ菌グ！？君との大冒険！</title><a href="/ja-jp/news/7011">2026-11-22</a>'}
        result = _verify_article_identity(payload, '7011', html)
        self.assertTrue(result['verified'])
        self.assertEqual(result['method'], 'cid')
        mismatch = _verify_article_identity(payload, '9569', html)
        self.assertFalse(mismatch['verified'])
        self.assertEqual(mismatch['reason'], 'article_id_mismatch')

    def test_title_without_article_id_is_not_enough(self):
        payload = {'title': '丹青渡 バージョンアップデート', 'displayTime': '2026-10-15'}
        html = {'ok': True, 'status': 200,
                'html': '<title>丹青渡 バージョンアップデート</title>2026-10-15'}
        result = _verify_article_identity(payload, '9560', html)
        self.assertTrue(result['verified'])
        self.assertEqual(result['method'], 'title_published')
        self.assertFalse(_verify_article_identity(payload, '9560',
                          {'ok': True, 'status': 200, 'html': '<title>別記事</title>'})['verified'])

    def test_url_verification_updates_named_mapping_without_current_adoption(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '7011', 'title': 'キノコ菌グ！？君との大冒険！ バージョンアップデート'}])
            return {'ok': True, 'status': 200, 'bytes': 20, 'payload': {
                'content': '新バージョン「キノコ菌グ！？君との大冒険！」 日本語 Asia 2026/11/22'}}
        report = audit(fetcher=fetch, today=dt.date(2026, 11, 23),
                       article_fetcher=lambda url: article_html('7011'))
        named = report['details'][0]['diagnostics']['named_version']
        self.assertTrue(named['cid_url_mapping_verified'])
        self.assertEqual(named['status'], 'official_named')
        self.assertFalse(named['accepted_as_current'])
        self.assertEqual(report['api_body_verification_successes'], 1)
        self.assertEqual(report['candidates'], [])

    def test_named_version_state_does_not_adopt_future_release(self):
        named = {'named_version': 'キノコ菌グ！？君との大冒険！',
                 'announced_release_date': '2026-11-25'}
        self.assertEqual(_classify_named_version(named, dt.date(2026, 11, 23), True), 'scheduled')
        self.assertEqual(_classify_named_version(named, dt.date(2026, 11, 26), True), 'released_candidate')
        self.assertEqual(_classify_named_version(named, dt.date(2026, 11, 23), False), 'unverified')

    def test_named_version_state_never_marks_current(self):
        def fetch(url):
            if '/bulletin?' in url:
                return listing([{'cid': '1'}])
            return {'ok': True, 'status': 200, 'bytes': 1,
                    'payload': {'content': '新バージョン「丹青渡」公開 2026/10/15 日本語 Asia'}}
        report = audit(fetcher=fetch,
                       today=dt.date(2026, 11, 23), article_fetcher=lambda _url: article_html('1'))
        named = report['details'][0]['diagnostics']['named_version']
        self.assertFalse(named['accepted_as_current'])

    def test_release_date_is_bound_to_named_version_context(self):
        mushroom = _extract_named_version({'content':
            '新バージョン「キノコ菌グ！？君との大冒険！」の注目情報。'
            '本ページは2026/10/06より常設公開。'
            '新バージョン「キノコ菌グ！？君との大冒険！」が2026年11月25日に公開されます。'}, '7011')
        self.assertEqual(mushroom['announced_release_date'], '2026-11-25')

        danqing = _extract_named_version({'content':
            '新バージョン「丹青渡」が2026年10月15日に公開されます。'}, '7014')
        self.assertEqual(danqing['announced_release_date'], '2026-10-15')

        no_release = _extract_named_version({'content':
            '新バージョン「キノコ菌グ！？君との大冒険！」注目情報。'
            '報酬受取期間：2026/11/21～2026/11/25'}, '9569')
        self.assertIsNone(no_release['announced_release_date'])


if __name__ == '__main__':
    unittest.main()
