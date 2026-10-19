#!/usr/bin/env python3
"""V48 translation review/export and evidence-checked import. Never changes events.json."""
import argparse, csv, datetime as dt, json, re
from pathlib import Path

JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
LATIN = re.compile(r"[A-Za-z]{3,}")
ALLOWED = {'genshin','wuwa','hsr','zzz','nte','arknights','endfield'}

def candidates(events, labels):
    rows=[]; seen=set()
    for e in events:
        game=e.get('game',''); name=e.get('name','')
        if not isinstance(name,str) or not LATIN.search(name) or JP.search(name):continue
        key=(game,name)
        if key in seen:continue
        seen.add(key)
        match=labels.get(game,{}).get(name,{})
        if isinstance(match,dict) and match.get('name'):continue
        rows.append({'game':game,'english_name':name,'japanese_name':'','source_url':'','source_type':'','reviewed_on':'','notes':''})
    return rows

def check_row(row, originals):
    game=row['game'].strip(); en=row['english_name'].strip(); ja=row['japanese_name'].strip()
    source=row['source_url'].strip(); typ=row['source_type'].strip(); date=row['reviewed_on'].strip()
    if game not in ALLOWED or (game,en) not in originals: raise ValueError('Unknown original game/name')
    if not ja or not JP.search(ja):raise ValueError('Japanese name required')
    if not source.startswith('https://') or any(c.isspace() for c in source):raise ValueError('HTTPS evidence URL required')
    if typ not in ('official','jp_wiki'):raise ValueError('source_type must be official or jp_wiki')
    try:dt.date.fromisoformat(date)
    except ValueError:raise ValueError('reviewed_on must be YYYY-MM-DD')
    return game,en,ja

def apply_review(rows, events, labels):
    originals={(e.get('game'),e.get('name')) for e in events}
    updated=json.loads(json.dumps(labels,ensure_ascii=False)); applied=[]
    for row in rows:
        if not row['japanese_name'].strip():continue
        game,en,ja=check_row(row,originals)
        existing=updated.setdefault(game,{}).get(en)
        if existing and existing.get('name') and existing['name']!=ja:
            raise ValueError('Existing translation conflict: '+game+'/'+en)
        if existing and existing.get('name')==ja:continue
        updated[game][en]={'name':ja}
        applied.append({'game':game,'english_name':en,'japanese_name':ja,'source_url':row['source_url'],'source_type':row['source_type'],'reviewed_on':row['reviewed_on']})
    return updated,applied

def main():
    p=argparse.ArgumentParser();p.add_argument('--events',default='events.json');p.add_argument('--labels',default='labels_ja.json')
    p.add_argument('--output',default='.reports/calendar-v48/translation_candidates.csv');p.add_argument('--apply-reviewed',help='CSV with checked Japanese names and source URLs')
    a=p.parse_args();events=json.loads(Path(a.events).read_text(encoding='utf-8'));labels=json.loads(Path(a.labels).read_text(encoding='utf-8'))
    if a.apply_reviewed:
        with open(a.apply_reviewed,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        try: updated,applied=apply_review(rows,events,labels)
        except (ValueError,KeyError) as ex:print('REVIEW_REJECTED:',ex);return 1
        if applied:
            Path(a.labels).write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        evidence=Path('.reports/calendar-v48/applied_evidence.json');evidence.parent.mkdir(parents=True,exist_ok=True)
        evidence.write_text(json.dumps(applied,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('V48 REVIEWED_APPLIED',len(applied),'events.json untouched; source URLs are user-reviewed, not automatically verified')
        return 0
    rows=candidates(events,labels);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['game','english_name','japanese_name','source_url','source_type','reviewed_on','notes']);writer.writeheader();writer.writerows(rows)
    print('V48 TRANSLATION REVIEW: CANDIDATES',len(rows),'OUTPUT',out,'MODE=READ_ONLY')
    return 0
if __name__=='__main__':raise SystemExit(main())
