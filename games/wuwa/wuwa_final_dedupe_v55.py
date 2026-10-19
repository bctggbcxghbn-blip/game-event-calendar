"""V55: conservative post-import Wuwa duplicate cleanup.

Only remove an unverified external-API copy when an independently identified
official entry matches the translated name, calendar dates and event category.
Other games, distinct rerun periods, and ambiguous duplicates are untouched.
"""
import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def display_name(event, labels):
    mapping = labels.get('wuwa', {})
    for name in (event.get('original_name'), event.get('name')):
        if isinstance(name, str) and name in mapping:
            entry = mapping[name]
            if isinstance(entry, dict) and isinstance(entry.get('name'), str):
                return entry['name']
    return event.get('name', '')


def category(kind):
    k = str(kind or '').strip().lower()
    if k in ('イベント', 'event'): return 'event'
    if k in ('ガチャ', 'gacha', '集音', '跳躍'): return 'gacha'
    return k


def official(event):
    status = str(event.get('source_status', ''))
    url = str(event.get('official_url', ''))
    return (status.startswith('公式') and
            url.startswith('https://wutheringwaves.kurogames.com/jp/main/news/detail/'))


def unverified_api(event):
    return str(event.get('source_status', '')) == '外部API・要確認' and str(event.get('id', '')).startswith('activity-')


def dedupe(events, labels):
    groups = defaultdict(list)
    for idx, event in enumerate(events):
        if event.get('game') != 'wuwa': continue
        key = (display_name(event, labels), event.get('start'), event.get('end'), category(event.get('kind')))
        groups[key].append(idx)
    drop = set()
    reports = []
    for key, indexes in groups.items():
        officials = [i for i in indexes if official(events[i])]
        api = [i for i in indexes if unverified_api(events[i])]
        # Require exactly one official and one unverified copy; fail closed for ambiguous groups.
        if len(indexes) == 2 and len(officials) == 1 and len(api) == 1:
            drop.add(api[0])
            reports.append({'name':key[0], 'start':key[1], 'end':key[2],
                            'kind':key[3], 'kept':events[officials[0]].get('id'),
                            'removed':events[api[0]].get('id')})
    return [event for idx, event in enumerate(events) if idx not in drop], reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'events.json'
    labels_path = ROOT / 'labels_ja.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    labels = json.loads(labels_path.read_text(encoding='utf-8'))
    updated, reports = dedupe(events, labels)
    print('WUWA V55 SAFE SOURCE DEDUPE MODE=' + ('APPLY' if args.apply else 'DRY_RUN'))
    for r in reports:
        print('MATCH', r['name'], r['start'], r['end'], 'KEEP='+str(r['kept']), 'REMOVE='+str(r['removed']))
    print(f'SUMMARY BEFORE={len(events)} AFTER={len(updated)} REMOVABLE={len(reports)}')
    if args.apply and reports:
        backup = path.with_suffix('.json.v55.bak')
        shutil.copy2(path, backup)
        tmp = path.with_suffix('.json.v55.tmp')
        try:
            tmp.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            # Check the result before replacing the original.
            check = json.loads(tmp.read_text(encoding='utf-8'))
            assert isinstance(check, list) and len(check) == len(events)-len(reports)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        print('APPLIED backup='+str(backup.relative_to(ROOT)))
    else:
        print('NO_CHANGES' if args.apply else 'DRY_RUN_COMPLETE')


if __name__ == '__main__':
    main()
