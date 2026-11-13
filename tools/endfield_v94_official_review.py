#!/usr/bin/env python3
"""V94: conservative official-announcement end-date review. Never edits events.json."""
import json
from pathlib import Path

SOURCE = 'https://endfield.gryphline.com/ja-jp/news/9560'

def build(root):
    p = root / 'games/endfield/v89_verified_candidates.json'
    candidates = json.loads(p.read_text(encoding='utf-8'))['events']
    calendar = json.loads((root / 'events.json').read_text(encoding='utf-8'))
    if not isinstance(calendar, list):
        raise ValueError('events.json must be a list')
    existing = {e.get('id'): e for e in calendar if isinstance(e, dict)}
    results = []
    for e in candidates:
        current = existing.get(e['id'])
        end = current.get('end') if current else None
        results.append({'id':e['id'], 'title':e['title'], 'registered':bool(current),
            'calendar_end':end, 'end_condition':e.get('end_condition'),
            'official_reference':SOURCE, 'review_status':'already_dated' if end else 'date_not_verified',
            'note':'Official notice gives a relative ending condition; do not infer a calendar date.' if not end else 'Existing end date; verify separately.'})
    return {'version':94,'mode':'read_only','official_reference':SOURCE,
            'checked_count':len(results),'still_undated':sum(not x['calendar_end'] for x in results),
            'items':results}

def main():
    root=Path(__file__).resolve().parents[1]
    report=build(root)
    out=root/'artifacts/endfield-v94'
    out.mkdir(parents=True,exist_ok=True)
    (out/'official-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Endfield V94 official-source review','',f"Source: {SOURCE}", '',f"Undated: {report['still_undated']} / {report['checked_count']}",'', 'This audit does not fetch live announcements and does not edit events.json.', '']
    lines += [f"- {x['title']}: {x['review_status']} / {x['end_condition']}" for x in report['items']]
    (out/'official-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f"V94 REVIEW: {report['checked_count']} candidates, {report['still_undated']} without verified end dates; NO_WRITES")

if __name__=='__main__': main()
