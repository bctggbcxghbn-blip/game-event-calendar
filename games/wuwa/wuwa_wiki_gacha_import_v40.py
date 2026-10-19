#!/usr/bin/env python3
"""V40: period-aware Wiki date-only gacha importer. Dry-run by default.

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
# Known official source identity: do not re-import a specific published banner
# merely because a source stored a different date range or time convention.
# This is narrowly scoped to the confirmed Ver3.7 first-phase weapon article.
PROTECTED_OFFICIAL_IDS = {
    ('3.7前', 'weapon', '曇斬'): 'wuwa-v13-5c1c98be8c784e42',
}

OFFICIAL_ALIASES = {
    ('3.7前', 'character', '千咲'): ['黄昏時に落ちる糸'],
    ('3.7前', 'character', 'ユーノ'): ['移りゆく月相と共に'],
}


def _date(value):
    # Official records may contain JST timestamps; compare calendar dates only.
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def _same_period(rec, event):
    # Inclusive overlap of >=2 days, or identical single-day windows.
    # A shared boundary day between consecutive phases is NOT a duplicate.
    a, b = _date(rec['start']), _date(rec['end'])
    c, d = _date(event.get('start')), _date(event.get('end'))
    if not all((a, b, c, d)) or a > b or c > d:
        return False  # Unknown dates cannot safely prove a duplicate.
    overlap = (min(b, d) - max(a, c)).days + 1
    return overlap >= 2 or (a == b == c == d)


def source_identity_hold(record, events):
    key = (record['phase'], record['kind'], record['name'])
    protected = PROTECTED_OFFICIAL_IDS.get(key)
    if not protected:
        return None
    for e in events:
        if isinstance(e, dict) and e.get('game') == 'wuwa' and e.get('id') == protected:
            return e
    return None


def same_name_period_diagnostics(record, events):
    target = v35.norm(record['name'])
    for e in events:
        if not isinstance(e, dict) or e.get('game') != 'wuwa':
            continue
        if str(e.get('kind', '')).lower() not in ('gacha', 'banner', 'character_gacha', 'weapon_gacha'):
            continue
        names = [v35.norm(e.get(k, '')) for k in ('name', 'original_name', 'banner_name', 'pickup', 'title') if isinstance(e.get(k, ''), str)]
        if target not in names:
            continue
        start, end = _date(e.get('start')), _date(e.get('end'))
        print('PERIOD_COMPARE', record['phase'], record['kind'].upper(), record['name'],
              'WIKI=' + record['start'] + '..' + record['end'],
              'EXISTING_ID=' + str(e.get('id', '?')),
              'EXISTING=' + str(e.get('start', '?')) + '..' + str(e.get('end', '?')),
              'OVERLAP=' + str(_same_period(record, e)),
              'DATES_VALID=' + str(bool(start and end and start <= end)))


def existing_matches(record, events):
    # A name match alone is never a duplicate: reruns belong to new periods.
    aliases = OFFICIAL_ALIASES.get((record['phase'], record['kind'], record['name']), [])
    targets = [v35.norm(record['name'])] + [v35.norm(a) for a in aliases]
    matched = []
    for e in events:
        if not isinstance(e, dict) or e.get('game') != 'wuwa':
            continue
        if not _same_period(record, e):
            continue
        # Only gacha entries, not event/challenge names.
        ekind = str(e.get('kind', '')).lower()
        if ekind not in ('gacha', 'banner', 'character_gacha', 'weapon_gacha') and 'gacha' not in ekind:
            continue
        event_type = str(e.get('gacha_type', '')).lower()
        if event_type in ('character', 'weapon') and event_type != record['kind']:
            continue
        fields = [e.get(k, '') for k in ('name', 'original_name', 'banner_name', 'pickup', 'title')]
        normalized = [v35.norm(f) for f in fields if isinstance(f, str) and f]
        # Exact name/alias or clear name inside a banner title. Never fuzzy-match 1-char names.
        if any(t and (t == f or (len(t) >= 3 and t in f)) for t in targets for f in normalized):
            matched.append(str(e.get('id', '?')))
    return matched


def record_id(rec):
    canonical = '|'.join((rec['phase'], rec['kind'], v35.norm(rec['name']), rec['start'], rec['end']))
    return 'wuwa-wiki-gacha-' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]


def save_atomic(path, events):
    # Backup and atomic replacement in the same filesystem; never touch unrelated entries.
    backup = path.with_suffix(path.suffix + '.v40.bak')
    shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(prefix='.wuwa-v40-', suffix='.json', dir=str(path.parent))
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
    print('WUWA V40 WIKI GACHA IMPORT MODE=' + ('APPLY' if args.apply else 'DRY_RUN'))
    print('WIKI_DATE_ONLY: no JST hours inferred; official records never overwritten')
    print('DEDUPE: name + matching period (>=2 overlapping days); reruns in distinct periods allowed')
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
    if not records:
        print('STOP: no parseable Wiki gacha rows; refusing all writes')
        return 2
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
        protected = source_identity_hold(r, events)
        same_name_period_diagnostics(r, events)
        if protected is not None:
            counts['duplicate'] += 1
            print('HOLD SOURCE_IDENTITY', r['phase'], r['kind'].upper(), r['name'],
                  'EXISTING_ID=' + str(protected['id']),
                  'WIKI=' + r['start'] + '..' + r['end'],
                  'EXISTING=' + str(protected.get('start')) + '..' + str(protected.get('end')))
        elif rid in ids or matches:
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
