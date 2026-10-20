#!/usr/bin/env python3
"""V70: audit NTE event presence without changing events.json."""
import argparse, json
from pathlib import Path

EXPECTED = {
 'nte-official-v14-treasure': '炭団子の秘宝',
 'nte-official-v14-stamina': 'スタミナブースト',
 'nte-official-v14-pixel': 'ピクセルオーバーフロー',
 'nte-official-v14-invitation': 'クロバネの招待状（Webイベント）',
}

def audit(events):
    nte = [e for e in events if e.get('game') == 'nte']
    results = []
    for key, name in EXPECTED.items():
        hits = [e for e in nte if e.get('id') == key or e.get('name') == name]
        results.append({'id': key, 'name': name, 'matches': len(hits), 'status': 'present' if len(hits)==1 else 'missing' if not hits else 'duplicate'})
    return {'total_events': len(events), 'nte_events': len(nte), 'candidates': results, 'safe_to_skip': all(r['status']=='present' for r in results)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--events',default='events.json');p.add_argument('--output',default='reports/nte-v70-audit.json');args=p.parse_args()
    data=json.loads(Path(args.events).read_text(encoding='utf-8'))
    if not isinstance(data,list): raise ValueError('events.json must be an array')
    result=audit(data)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
