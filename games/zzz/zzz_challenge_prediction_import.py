#!/usr/bin/env python3
"""Generate clearly labelled predicted ZZZ endgame rotations into events.json.

Uses a documented rotation anchor, NOT individually confirmed future notices.
Run without arguments to preview; use --apply to save.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JST = dt.timezone(dt.timedelta(hours=9))
ANCHOR = dt.date(2026, 10, 16)  # Observed Critical Node rotation
ROTATIONS = (
    ('shiyu', '式輿防衛戦・激変ノード', 0),
    ('deadly', '危局強襲戦', 7),
)
SOURCE = 'https://www.icy-veins.com/zenless-zone-zero/shiyu-defense-critical-node'

def normalized_label(value):
    value = re.sub(r'^【予測】', '', str(value or '').strip())
    return re.sub(r'\s+', '', value)

def filter_predictions(predicted, confirmed_records):
    confirmed_records = [x for x in confirmed_records if str(x.get('id', '')).startswith('zzz-official-')
                         or str(x.get('source_status', '')).startswith('HoYoLAB公式')]
    confirmed = {(x.get('game'), x.get('kind'), x.get('start'), normalized_label(x.get('name'))) for x in confirmed_records}
    ranges = [(x.get('start'), x.get('end'), normalized_label(x.get('name'))) for x in confirmed_records]
    def overlaps(a_start, a_end, b_start, b_end):
        return bool(a_start and a_end and b_start and b_end and a_start < b_end and b_start < a_end)
    return [x for x in predicted if (x['game'], x['kind'], x['start'], normalized_label(x.get('name'))) not in confirmed
            and not any(label == normalized_label(x.get('name')) and overlaps(x['start'], x['end'], start, end)
                       for start, end, label in ranges)]


def generate(today, horizon_days):
    result = []
    limit = today + dt.timedelta(days=horizon_days)
    for slug, label, offset in ROTATIONS:
        base = ANCHOR + dt.timedelta(days=offset)
        # Start at the cycle overlapping today, with one-cycle buffer.
        n = max(0, (today - base).days // 14 - 1)
        while True:
            start = base + dt.timedelta(days=n * 14)
            if start > limit:
                break
            end_exclusive = start + dt.timedelta(days=14)
            if end_exclusive > today:
                result.append({
                    'id': f'zzz-predicted-{slug}-{start:%Y%m%d}',
                    'game': 'zzz',
                    'name': f'【予測】{label}',
                    'start': start.isoformat(),
                    'end': end_exclusive.isoformat(),
                    'start_time': '05:00',
                    'end_time': '04:59',
                    'time_zone': 'Asia/Tokyo',
                    'kind': 'チャレンジ',
                    'source_status': '予測（14日周期から算出・公式個別日程未確認）',
                    'url': SOURCE,
                })
            n += 1
    return sorted(result, key=lambda x: (x['start'], x['name']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--days', type=int, default=90, help='Prediction horizon, default 90 days')
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error('--days must be 1..365')

    path = ROOT / 'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must be a JSON array')

    today = dt.datetime.now(JST).date()
    predicted = generate(today, args.days)
    predicted_ids = {x['id'] for x in predicted}
    # Only own our own predictions. Do not overwrite confirmed or other imports.
    old_predicted = [x for x in events if isinstance(x, dict) and str(x.get('id', '')).startswith('zzz-predicted-')]
    retained = [x for x in events if not (isinstance(x, dict) and str(x.get('id', '')).startswith('zzz-predicted-'))]
    confirmed_records = [x for x in retained if isinstance(x, dict)
        and x.get('game') == 'zzz' and x.get('kind') == 'チャレンジ'
        and not ('予測' in str(x.get('name', '')) or '予測' in str(x.get('source_status', '')))
        and (str(x.get('id', '')).startswith('zzz-official-') or str(x.get('source_status', '')).startswith('HoYoLAB公式'))]
    # Do not create a prediction when an official challenge covers the same window,
    # even if the official notice corrected the start date.
    filtered = filter_predictions(predicted, confirmed_records)
    result = retained + filtered
    result.sort(key=lambda x: (str(x.get('start', '')), str(x.get('game', '')), str(x.get('name', ''))))
    print('ANCHOR: 2026-10-16 Shiyu Defense rotation')
    print('NOTICE: Future dates are predictions, not official confirmations.')
    print(f'PREDICTIONS: {len(filtered)}; OLD PREDICTIONS: {len(old_predicted)}; CONFIRMED-DATE COLLISIONS: {len(predicted)-len(filtered)}')
    for record in filtered:
        print(f"PREDICTED: {record['name']} {record['start']} 05:00 -> {record['end']} 04:59 JST")
    if args.apply:
        if result == events:
            print('UNCHANGED: events.json already up to date.')
        else:
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print('UPDATED: events.json')
    else:
        print('PREVIEW ONLY. No files modified.')


if __name__ == '__main__':
    main()
