#!/usr/bin/env python3
"""Conservative official-announcement reconciliation for HSR.

Only reviewed entries are applied; this is NOT an automatic official-news crawler.
New announcement data must be reviewed and added to OFFICIAL below.
Run after the other event importers to preserve official metadata.
"""
import datetime as dt
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = 'https://hsr.hoyoverse.com/en-us/news/166468'
# Confirmed from the official Version 4.6 announcement. UTC+8 timestamps
# become JST by adding one hour. Server-time dates are kept as server dates
# until their timezone is verified; do not silently convert them.
OFFICIAL = [
    dict(names=['愛、幽霊とロボット', 'Love, Ghosts & Robots'], start='2026-09-28', end='2026-11-11', start_label='アップデート後', end_utc8='2026-11-11 03:59'),
    dict(names=['スターピースフェスティバル：ワンカット', 'Interastral Peace Gala: One Take'], start='2026-10-21', end='2026-11-11', end_utc8='2026-11-11 03:59'),
    dict(names=['Astral Imagea Park: Astral Trendible', '「星際幻寵」樂園：星際潮玩'], start='2026-09-28', end='2026-11-11', start_label='アップデート後', end_utc8='2026-11-11 06:00'),
    dict(names=['Astral Imagea Park: Park Souvenir'], start='2026-09-28', end='2026-11-11', start_label='アップデート後', end_utc8='2026-11-11 06:00'),
    dict(names=['Wishpower UP! Down with Voracity!'], start='2026-09-28', end='2026-11-11', start_label='アップデート後', end_utc8='2026-11-11 06:00'),
]

def normalize(s):
    return re.sub(r'[\s・:：!！?？「」『』\-–—]+', '', str(s)).casefold()

def jst(utc8):
    instant = dt.datetime.strptime(utc8, '%Y-%m-%d %H:%M') + dt.timedelta(hours=1)
    return instant.strftime('%Y-%m-%d'), instant.strftime('%H:%M')

def main():
    path = ROOT / 'events.json'
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('events.json must be a list')
    count = 0
    for item in rows:
        if not isinstance(item, dict) or item.get('game') != 'hsr':
            continue
        for official in OFFICIAL:
            names = {normalize(n) for n in official['names']}
            if not ({normalize(item.get('name', '')), normalize(item.get('original_name', ''))} & names):
                continue
            # Require exact dates. Never override a potentially different season.
            if (item.get('start'), item.get('end')) != (official['start'], official['end']):
                continue
            changed = False
            if official.get('start_label') and item.get('start_label') != official['start_label']:
                item['start_label'] = official['start_label']
                item.pop('start_time', None)  # avoid a contradictory guessed clock
                changed = True
            if official.get('end_utc8'):
                date, clock = jst(official['end_utc8'])
                if date == item['end'] and item.get('end_time') != clock:
                    item['end_time'] = clock
                    changed = True
            if changed:
                item['official_url'] = SOURCE
                item['source_status'] = '公式お知らせ・日時確認済み'
                count += 1
            break
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'HSR official events: {count} rows updated from reviewed official notice; no dates changed.')

if __name__ == '__main__':
    main()
