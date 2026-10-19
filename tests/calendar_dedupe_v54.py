"""V54: read-only duplicate audit of translated display entries."""
import json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def audit(events,labels):
    groups=defaultdict(list)
    for e in events:
        lookup=labels.get(e.get('game'),{})
        key=e.get('original_name') or e.get('name','')
        name=lookup.get(key,lookup.get(e.get('name',''),{})).get('name',e.get('name',''))
        kind=e.get('kind','')
        category='gacha' if kind.lower() in ('gacha','ガチャ','集音','跳躍') else 'other' if kind.lower() in ('other','その他') else 'event' if kind.lower() in ('event','イベント') else kind.lower()
        groups[(e.get('game'),name,e.get('start'),e.get('end'),category)].append(e.get('id',''))
    return [(key,ids) for key,ids in groups.items() if len(ids)>1]
if __name__=='__main__':
    events=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
    labels=json.loads((ROOT/'labels_ja.json').read_text(encoding='utf-8'))
    duplicates=audit(events,labels)
    print('V54 READ-ONLY DISPLAY DUPLICATE AUDIT:',len(duplicates),'groups')
    for (game,name,start,end,category),ids in duplicates:
        print('DUPLICATE',game,name,start,end,category,'IDS='+','.join(ids))
    print('SOURCE_DATA_UNCHANGED')
