import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('danqingdu_v72.json')

def merge(existing, incoming):
    if not isinstance(existing, list):
        raise ValueError('events.json must be a JSON list')
    seen = {(x.get('game'), x.get('id')) for x in existing if isinstance(x, dict)}
    result = list(existing)
    added = []
    for event in incoming:
        key = (event['game'], event['id'])
        if key not in seen:
            result.append(event)
            seen.add(key)
            added.append(event['name'])
    return result, added

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Write events.json; default preview only')
    args = p.parse_args()
    target = ROOT / 'events.json'
    existing = json.loads(target.read_text(encoding='utf-8'))
    incoming = json.loads(SOURCE.read_text(encoding='utf-8'))
    merged, added = merge(existing, incoming)
    print(f'Existing: {len(existing)} / Candidates: {len(incoming)} / New: {len(added)}')
    for name in added: print('ADD:', name)
    if args.apply and added:
        target.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Updated events.json')
    elif not args.apply:
        print('PREVIEW ONLY: use --apply to update events.json')

if __name__ == '__main__': main()
