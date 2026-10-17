#!/usr/bin/env python3
"""Preview ZZZ endgame challenge rotations; does not edit events.json.

The anchor is a verified Shiyu Defense rotation on 2026-10-16.
Future dates are predictions based on a 28-day cycle, NOT official confirmations.
"""
import argparse
from datetime import date, timedelta

ANCHOR = date(2026, 10, 16)
CYCLE_DAYS = 28


def preview(days: int) -> None:
    today = date.today()
    start = today - timedelta(days=28)
    finish = today + timedelta(days=days)
    print('SOURCE: https://www.icy-veins.com/zenless-zone-zero/shiyu-defense-critical-node')
    print('VERIFIED ANCHOR: 2026-10-16 Shiyu Defense reset')
    print('CAUTION: future rotations below are estimates, not official dates.')
    print('TIME: 04:00 Asia server time (UTC+8), 05:00 JST; verify before applying.')
    for offset in range(-12, 30):
        d = ANCHOR + timedelta(days=offset * CYCLE_DAYS // 2)
        if not start <= d <= finish:
            continue
        kind = '式輿防衛戦・激変ノード' if offset % 2 == 0 else '危局強襲戦'
        next_date = d + timedelta(days=14)
        label = 'CONFIRMED ANCHOR' if d == ANCHOR else 'ESTIMATED'
        print(f'{label} [{kind}] {d} 05:00 JST -> {next_date} 04:59 JST')
    print('PREVIEW ONLY. No files modified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=90)
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error('--days must be 1..365')
    preview(args.days)
