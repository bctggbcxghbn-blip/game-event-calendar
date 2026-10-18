#!/usr/bin/env python3
"""V36: conservative Wiki date-only gacha importer. Dry-run by default.

Requires wuwa_wiki_merge_preview_v35.py in the same directory.
Wiki is community-maintained; imported dates are NOT confirmed JST timestamps.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent
V35 = HERE / 'wuwa_wiki_merge_preview_v35.py'
spec = importlib.util.spec_from_file_location('wuwa_v35', V35)
if not V35.exists():
    raise SystemExit('ERROR: missing games/wuwa/wuwa_wiki_merge_preview_v35.py')
v35 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v35)

# These banner-to-character relationships are known from official article 5547.
# Only used to PREVENT duplicate imports, never to establish dates.
OFFICIAL_ALIASES = {
    ('3.7前', 'character', '千咲'): ['黄昏時に落ちる糸'],
    ('3.7前', 'character', 'ユーノ'): ['移りゆく月相と共に'],
}


def existing_matches(record, events):
    direct = v35.existing_match(record, events)
    if direct:
        return direct
    aliases = OFFICIAL_ALIASES.get((record['phase'], record['kind'], record['name']), [])
    if not aliases:
        return []
    matched = []
    for e in events:
        if not isinstance(e, dict) or e.get('game') != 'wuwa':
            continue
        fields = [e.get(k, '') for k in ('name', 'original_name', 'banner_name', 'pickup', 'title')]
        if any(v35.norm(a) == v35.norm(f) or (len(v35.norm(a)) >= 3 and v35.norm(a) in v35.norm(f))
               for a in aliases for f in fields if f):
            matched.append(e.get('id', '?'))
    return matched


def record_id(rec):
    canonical = '|'.join((rec['phase'], rec['kind'], v35.norm(rec['name']), rec['start'], rec['end']))
    return 'wuwa-wiki-gacha-' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]


def save_atomic(path, events):
    # Backup and atomic replacement in the same filesystem; never touch unrelated entries.
    backup = path.with_suffix(path.suffix + '.v36.bak')
    shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(prefix='.wuwa-v36-', suffix='.json', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        verified = json.loads(Path(tmp).read_text(encoding='utf-8'))
        if not isinstance(verified, list) or len(verified) != len(events):
            raise ValueError('write verification failed')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return backup


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true', help='Write eligible candidates to events.json')
    ap.add_argument('--version', default='Ver3.7')
    ap.add_argument('--events', default='events.json')
    ap.add_argument('--html-file', help='Offline Wiki HTML fixture')
    args = ap.parse_args()
    if not v35.VERSION.fullmatch(args.version):
        ap.error('invalid version, e.g. Ver3.7')
    path = Path(args.events)
    print('WUWA V36 WIKI GACHA IMPORT MODE=' + ('APPLY' if args.apply else 'DRY_RUN'))
    print('WIKI_DATE_ONLY: no JST hours inferred; official records never overwritten')
    try:
        if args.html_file:
            raw = Path(args.html_file).read_text(encoding='utf-8')
        else:
            req = urllib.request.Request(v35.BASE + args.version,
                                         headers={'User-Agent': 'Mozilla/5.0 WuwaCalendar/1.0'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode('utf-8', 'replace')
        events = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
            raise ValueError('events.json must be an array of objects')
    except Exception as exc:
        print('ERROR FETCH_OR_READ:', repr(exc))
        return 1
    records, holds = v35.get_rows(raw, args.version)
    print('WIKI_RECORDS:', len(records), 'EXISTING_EVENTS:', len(events))
    for h in holds:
        print('HOLD PARSE:', *h)
    # Fail closed if any source cell cannot be parsed.
    if holds:
        print('STOP: unparsed Wiki cells; refusing all writes')
        return 2
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    ids = {e.get('id') for e in events}
    seen = set()
    additions = []
    counts = dict(duplicate=0, expired=0, manual=0)
    for r in records:
        key = (r['phase'], r['kind'], v35.norm(r['name']), r['start'], r['end'])
        if key in seen:
            continue
        seen.add(key)
        rid = record_id(r)
        matches = existing_matches(r, events)
        if rid in ids or matches:
            counts['duplicate'] += 1
            print('HOLD DUPLICATE', r['phase'], r['kind'].upper(), r['name'], 'IDS=' + ','.join(map(str, matches[:5])))
        elif r['end'] < today:
            counts['expired'] += 1
            print('HOLD EXPIRED', r['phase'], r['kind'].upper(), r['name'])
        elif len(v35.norm(r['name'])) < 2:
            # Short labels like "心" can be ambiguous; do not import automatically.
            counts['manual'] += 1
            print('HOLD SHORT_NAME_REVIEW', r['phase'], r['kind'].upper(), r['name'])
        else:
            event = dict(id=rid, game='wuwa', name=r['name'], kind='gacha',
                         start=r['start'], end=r['end'],
                         source_status='日本語Wiki・日付のみ・要確認',
                         time_zone='unverified_date_only',
                         source_url=v35.BASE + args.version,
                         gacha_type=r['kind'], phase=r['phase'])
            additions.append(event)
            print('CANDIDATE', r['phase'], r['kind'].upper(), r['name'], r['start'], '->', r['end'])
    print('SUMMARY: BEFORE=%d UNIQUE=%d CANDIDATE=%d DUPLICATE_HOLD=%d EXPIRED_HOLD=%d MANUAL_HOLD=%d' %
          (len(events), len(seen), len(additions), counts['duplicate'], counts['expired'], counts['manual']))
    if not args.apply:
        print('DRY_RUN_COMPLETE: events.json unchanged; add --apply only after reviewing candidates')
        return 0
    if not additions:
        print('APPLY_NO_CHANGES: no eligible Wiki gacha')
        return 0
    # A stale local checkout could overwrite newer data. Workflow must run after other importers,
    # with a single job responsible for committing the final events.json.
    output = events + additions
    if len({e.get('id') for e in output}) != len(output):
        print('ERROR: duplicate event IDs; refusing write')
        return 3
    try:
        backup = save_atomic(path, output)
    except Exception as exc:
        print('ERROR WRITE:', repr(exc))
        return 4
    print('APPLY_COMPLETE: BEFORE=%d ADDED=%d AFTER=%d BACKUP=%s' %
          (len(events), len(additions), len(output), backup))
    return 0


if __name__ == '__main__':
    sys.exit(main())
