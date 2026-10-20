#!/usr/bin/env python3
"""V66: add officially verified Hunter Pass event. Default dry run."""
import argparse, json, pathlib, hashlib

NAME = 'Ver.1.4 ハンター褒章'
SOURCE = 'https://nte.perfectworld.com/jp/article/news/gamenews/20260929/264412.html'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='events.json')
    ap.add_argument('--apply', action='store_true', help='write events.json (creates backup)')
    args = ap.parse_args()
    path = pathlib.Path(args.events)
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise SystemExit('Unsupported events.json format: expected list')
    existing = [e for e in events if e.get('game') == 'nte' and ('ハンター褒章' in e.get('name','') or 'hunter pass' in e.get('name','').lower())]
    if existing:
        print('SKIP: possible existing Hunter Pass entry:', [e.get('name') for e in existing]); return
    event = {
        'id': 'nte-hunter-pass-v14-20260930', 'game': 'nte', 'name': NAME,
        'start': '2026-09-30', 'end': '2026-11-11', 'kind': 'イベント',
        'source_status': '公式確認済み', 'source': SOURCE,
        'note': '開始: 9/30アップデート後（予定メンテナンス終了12:00 JST）。終了: 11/10 24:59 JST = 11/11 00:59 JST。日付表示は終了日11/11。'
    }
    print(('APPLY' if args.apply else 'DRY RUN'), json.dumps(event, ensure_ascii=False))
    if args.apply:
        backup = path.with_name(path.name+'.v66.bak')
        if backup.exists(): raise SystemExit(f'Backup already exists: {backup}')
        backup.write_bytes(path.read_bytes())
        events.append(event)
        path.write_text(json.dumps(events, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print('Written:', path, 'Backup:', backup)

if __name__ == '__main__': main()
