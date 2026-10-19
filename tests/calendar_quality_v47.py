#!/usr/bin/env python3
"""Non-mutating calendar quality report. Never infers translations or gacha rarity."""
import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path

ASCII_WORD = re.compile(r"[A-Za-z]{3,}")
JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
GACHA = re.compile(r"gacha|ガチャ|集音|跳躍|祈願|キャラ|武器", re.I)


def analyze(events, labels=None):
    labels = labels or {}
    issues = []
    seen_ids = set()
    seen_exact = set()
    counts = collections.Counter()
    for i, e in enumerate(events):
        game = e.get('game', '')
        name = e.get('name', '')
        kind = e.get('kind', '')
        eid = e.get('id', '')
        counts[game] += 1
        if not eid or eid in seen_ids:
            issues.append({'level': 'error', 'type': 'duplicate_or_missing_id', 'index': i, 'id': eid})
        seen_ids.add(eid)
        try:
            start = dt.date.fromisoformat(e['start'])
            end = dt.date.fromisoformat(e['end'])
            if end < start: raise ValueError('reversed')
        except (KeyError, TypeError, ValueError):
            issues.append({'level': 'error', 'type': 'invalid_dates', 'index': i, 'id': eid})
        identity = (game, str(name).strip(), e.get('start'), e.get('end'), kind)
        if identity in seen_exact:
            issues.append({'level': 'review', 'type': 'same_name_period_kind', 'index': i, 'id': eid})
        seen_exact.add(identity)
        if ASCII_WORD.search(name) and not JP.search(name):
            translation = labels.get(game, {}).get(name)
            if not isinstance(translation, dict) or not translation.get('name'):
                issues.append({'level': 'review', 'type': 'english_name_untranslated', 'index': i, 'id': eid, 'name': name, 'game': game})
        if GACHA.search(str(kind)) or GACHA.search(str(name)):
            if not any(key in e for key in ('rarity', 'is_rerun', 'gacha_status', 'release_type')):
                issues.append({'level': 'info', 'type': 'gacha_release_status_unverified', 'index': i, 'id': eid})
    return {'total': len(events), 'by_game': dict(sorted(counts.items())), 'issue_counts': dict(sorted(collections.Counter(x['type'] for x in issues).items())), 'issues': issues}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', default='events.json')
    ap.add_argument('--labels', default='labels_ja.json')
    ap.add_argument('--output', default='.reports/calendar-v47/report.json')
    args = ap.parse_args()
    events = json.loads(Path(args.events).read_text(encoding='utf-8'))
    labels = json.loads(Path(args.labels).read_text(encoding='utf-8')) if Path(args.labels).exists() else {}
    report = analyze(events, labels)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('V47 QUALITY AUDIT (READ-ONLY)')
    print('TOTAL:', report['total'], 'BY_GAME:', report['by_game'])
    for typ, count in report['issue_counts'].items():
        print('ISSUE', typ, count)
    print('REPORT:', output)
    errors = [x for x in report['issues'] if x['level'] == 'error']
    print('STATUS:', 'ERROR' if errors else 'OK_WITH_REVIEW_ITEMS')
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
