#!/usr/bin/env python3
"""ZZZ official update maintenance importer. Preview by default; --apply writes events.json."""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'games' / 'hsr'))
from hsr_maintenance_detail_probe import DETAIL, LIST, get_json
from hsr_maintenance_time_preview import content_text

UTC8 = dt.timezone(dt.timedelta(hours=8))
JST = dt.timezone(dt.timedelta(hours=9))
TITLE = re.compile(r'pre.download\s*&\s*update notice|update\s*(?:and|&)\s*maintenance|maintenance notice|メンテナンス|アップデート.*お知らせ|维护公告', re.I)
START = re.compile(r'(?:\[\s*Version Update Time\s*\]|Version Update Time|Update Maintenance (?:Begins|Starts)|Maintenance (?:Begins|Starts))\s*[:：]?\s*(20\d{2})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})\s*\(?\s*UTC\s*\+\s*8\s*\)?', re.I)
DURATION = re.compile(r'(?:estimate(?:d)?\s*(?:it\s+will\s+|to\s+)?take|approximately|about|around|roughly)\s*(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*hours?|(?:预计|约)\s*(\d{1,2})\s*小时', re.I)
WORDS = dict(one=1,two=2,three=3,four=4,five=5,six=6,seven=7,eight=8,nine=9,ten=10,eleven=11,twelve=12)

def parse_window(body):
    match = START.search(body)
    if not match:
        return None, 'No explicit update start in UTC+8'
    try:
        start = dt.datetime(*map(int, match.groups()), tzinfo=UTC8)
    except ValueError:
        return None, 'Invalid start time'
    duration = DURATION.search(body[match.end():match.end()+400])
    if not duration:
        return None, 'No estimated duration near update time'
    raw = next(v for v in duration.groups() if v)
    hours = WORDS.get(raw.lower(), int(raw) if raw.isdigit() else 0)
    if not 1 <= hours <= 12:
        return None, 'Unreasonable duration'
    return (start.astimezone(JST), (start+dt.timedelta(hours=hours)).astimezone(JST), hours), None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--limit', type=int, default=50)
    args = ap.parse_args()
    if not 1 <= args.limit <= 50:
        ap.error('--limit must be 1..50')
    path = ROOT/'events.json'
    events = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(events, list):
        raise ValueError('events.json must be an array')
    seen = set()
    existing = {str(e.get('id')) for e in events if isinstance(e, dict)}
    added = []
    today = dt.datetime.now(JST)
    for typ in (1,2,3):
        try:
            response = get_json(LIST+'?'+urlencode({'gids':8,'type':typ,'page_size':args.limit}))
            items = response.get('list', [])
            print(f'NEWS TYPE {typ}: {len(items)} articles')
        except Exception as exc:
            print(f'WARNING NEWS TYPE {typ}: {exc}')
            continue
        for item in items:
            post = item.get('post',item) if isinstance(item,dict) else {}
            if not isinstance(post,dict):
                continue
            pid = str(post.get('post_id') or post.get('id') or '')
            title = str(post.get('subject') or post.get('title') or '')
            if not pid.isdigit() or pid in seen:
                continue
            seen.add(pid)
            if not TITLE.search(title):
                continue
            try:
                detail = get_json(DETAIL+'?'+urlencode({'post_id':pid}))
                parsed, reason = parse_window(content_text(detail))
            except Exception as exc:
                print(f'SKIP {pid}: {exc}')
                continue
            if not parsed:
                print(f'SKIP {pid}: {reason}')
                continue
            start,end,hours = parsed
            print(f'FOUND {title}: {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} JST')
            if end < today:
                print('SKIP: Already ended')
                continue
            if start > today+dt.timedelta(days=120):
                print('SKIP: More than 120 days ahead')
                continue
            identifier = f'zzz-maintenance-{start:%Y%m%d}'
            if identifier in existing or any(e.get('game')=='zzz' and e.get('kind')=='メンテナンス' and e.get('start')==start.date().isoformat() for e in events if isinstance(e,dict)):
                print('SKIP: Already registered')
                continue
            record = {'id':identifier,'game':'zzz','name':'ゼンゼロ アップデートメンテナンス（終了予定）','start':start.date().isoformat(),'end':end.date().isoformat(),'start_time':start.strftime('%H:%M'),'end_time':end.strftime('%H:%M'),'time_zone':'Asia/Tokyo','kind':'メンテナンス','source_status':f'HoYoLAB公式・終了時刻は約{hours}時間の予定','official_url':f'https://www.hoyolab.com/article/{pid}','url':f'https://www.hoyolab.com/article/{pid}'}
            added.append(record)
            existing.add(identifier)
            print(f'CANDIDATE: {record["name"]} {record["start"]}')
    if args.apply and added:
        events.extend(added)
        events.sort(key=lambda e:(str(e.get('start','')),str(e.get('game','')),str(e.get('name',''))))
        path.write_text(json.dumps(events,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'ADDED: {len(added)} record(s). events.json updated.')
    else:
        print(f'{"ADDED" if args.apply else "PREVIEW"}: {len(added)} record(s). No files modified.')

if __name__=='__main__':
    main()
