#!/usr/bin/env python3
"""NTE Ver.1.4 official announcement importer. Safe, repeatable, offline.

Dates are sourced from the linked Japanese official announcement. Update-relative
starts and server-time events are date-only; no unannounced JST clock is inferred.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://nte.perfectworld.com/jp/article/news/gamenews/20260929/264412.html'

# id suffix, name, kind, start date, end date, start label, end time, timezone
ITEMS = [
    ('kurobane', 'クロバネ（新規）', '新キャラガチャ', '2026-09-30', '2026-10-21', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('requiem', 'レクイエム（復刻）', '復刻キャラガチャ', '2026-09-30', '2026-10-21', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('sin-punishment', '罪と罰（新規弧盤）', '新武器ガチャ', '2026-09-30', '2026-10-21', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('last-rose', 'ラスト・ローズ（復刻弧盤）', '復刻武器ガチャ', '2026-09-30', '2026-10-21', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('seven-days', '7Daysボーナス', 'ログイン', '2026-09-30', '2026-11-11', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('puka-festival', 'プカ遊園祭', 'イベント', '2026-09-30', '2026-11-11', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('extreme-rank', '極限昇段戦', 'イベント', '2026-09-30', '2026-11-11', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('treasure', '炭団子の秘宝', 'イベント', '2026-10-08', '2026-11-11', '11:00', '06:59', 'JST'),
    ('stamina', 'スタミナブースト', 'イベント', '2026-10-05', '2026-10-19', '05:00', '04:59', 'サーバー時間'),
    ('pixel', 'ピクセルオーバーフロー', 'イベント', '2026-10-19', '2026-10-26', '05:00', '04:59', 'サーバー時間'),
    ('porsche-new', 'Porscheコラボ：ファントムラン', 'イベント', '2026-09-30', '2026-11-11', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('porsche-return', 'Porscheコラボ：エバードライブ（復刻）', 'イベント', '2026-09-30', '2026-11-11', 'Ver.1.4アップデート後', '06:59', 'JST'),
    ('invitation', 'クロバネの招待状（Webイベント）', 'イベント', '2026-09-30', '2026-11-11', '12:00', '06:59', 'JST'),
    ('costume', 'クロバネ「蒼羽ソワレ」割引', 'イベント', '2026-10-07', '2026-11-11', '07:30', '06:59', 'JST'),
]


def official_events():
    out = []
    for slug, name, kind, start, end, start_label, end_clock, tz in ITEMS:
        item = {'id': 'nte-official-v14-' + slug, 'game': 'nte', 'name': name,
                'kind': kind, 'start': start, 'end': end,
                'source_status': 'NTE公式Ver.1.4', 'official_url': SOURCE,
                'start_label': start_label, 'end_time': end_clock,
                'time_zone': tz}
        if start_label != 'Ver.1.4アップデート後':
            item['start_time'] = start_label
        else:
            item['start_note'] = 'アップデート後（正確な開始時刻は未発表）'
        if tz == 'サーバー時間':
            item['end_note'] = 'サーバー時間（JSTへの換算なし）'
        out.append(item)
    return out


def merge(existing):
    if not isinstance(existing, list):
        raise ValueError('events.json must be a list')
    incoming = official_events()
    ids = {x['id'] for x in incoming}
    # Replace our own stable IDs only, never touch entries from other sources.
    output = [x for x in existing if x.get('id') not in ids] + incoming
    output.sort(key=lambda x: (x.get('start', ''), x.get('game', ''), x.get('id', '')))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--path', type=Path, default=ROOT / 'events.json')
    args = parser.parse_args()
    data = json.loads(args.path.read_text(encoding='utf-8'))
    output = merge(data)
    print(f'NTE V59 official Ver.1.4: {len(ITEMS)} items; total {len(data)} -> {len(output)}')
    if args.apply and output != data:
        args.path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('APPLIED')
    else:
        print('NO CHANGE' if args.apply else 'PREVIEW ONLY')


if __name__ == '__main__':
    main()
