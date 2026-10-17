#!/usr/bin/env python3
"""Read-only probe for four Wuthering Waves announcement categories.

Usage: python games/wuwa/wuwa_four_probe.py
Requires only Python 3 standard library. Does not modify events.json.
"""
import json
import re
import urllib.request
import urllib.error
from html import unescape

SOURCES = [
    ('Official news (EN)', 'https://wutheringwaves.kurogames.com/en/main/news'),
    ('Official site (EN)', 'https://wutheringwaves.kurogames.com/en/main'),
]
CATEGORIES = {
    'EVENT': ['event', 'events', 'イベント', '催し'],
    'GACHA': ['convene', 'featured', 'resonator', 'weapon', 'ガチャ', '集音'],
    'MAINTENANCE': ['maintenance', 'update', 'version', 'メンテナンス', 'アップデート'],
    'CHALLENGE': ['tower of adversity', 'whimpering wastes', 'tactical hologram', '逆境深塔', '深塔'],
}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; WuwaCalendarProbe/1.0)', 'Accept-Language': 'en-US,en;q=0.8'}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(1_500_000)
        return response.status, response.geturl(), raw.decode('utf-8', 'replace')


def strip_html(content):
    content = re.sub(r'<script\b[^>]*>.*?</script>', ' ', content, flags=re.I | re.S)
    content = re.sub(r'<style\b[^>]*>.*?</style>', ' ', content, flags=re.I | re.S)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', content)))


def main():
    print('WUWA 4-CATEGORY READ-ONLY PROBE')
    print('No event data will be changed.\n')
    combined = []
    for label, url in SOURCES:
        print(f'SOURCE: {label}\nURL: {url}')
        try:
            status, final_url, html = fetch(url)
            visible = strip_html(html)
            combined.append(visible)
            print(f'HTTP: {status} | Final URL: {final_url} | HTML chars: {len(html)} | Text chars: {len(visible)}')
            title = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
            if title:
                print('PAGE TITLE:', strip_html(title.group(1))[:150])
            print('TEXT SAMPLE:', visible[:280])
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f'FETCH ERROR: {type(exc).__name__}: {exc}')
        print()
    text = ' '.join(combined)
    print('=== FOUR CATEGORY CHECKS ===')
    for category, terms in CATEGORIES.items():
        found = [term for term in terms if term.casefold() in text.casefold()]
        print(f'{category}: ' + (f'KEYWORDS FOUND ({", ".join(found)})' if found else 'NO KEYWORDS FOUND'))
    print('\nNOTE: Keyword matches do NOT prove that article dates can be extracted.')
    print('NOTE: NO KEYWORDS FOUND may mean the website renders news with JavaScript.')
    print('NEXT: Inspect output to choose a reliable official news API/feed for each category.')


if __name__ == '__main__':
    main()
