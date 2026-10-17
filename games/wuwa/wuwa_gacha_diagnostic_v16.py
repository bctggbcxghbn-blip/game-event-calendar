#!/usr/bin/env python3
"""Read-only diagnostic for WuWa article 5547 banner sections."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wuwa_safe_import_v13 as base

def main():
    print('WUWA V16 GACHA DIAGNOSTIC / READ ONLY')
    print('No events.json changes. No apply mode.')
    try:
        title, body = base.article(5547)
    except Exception as exc:
        raise SystemExit('FETCH ERROR: '+repr(exc))
    print('ARTICLE:', title)
    headings = list(base.BANNER.finditer(body))
    print('MATCHED BANNER HEADINGS:', len(headings))
    for i, h in enumerate(headings, 1):
        seg = body[h.end():headings[i].start() if i < len(headings) else len(body)]
        periods = list(base.PERIOD.finditer(seg))
        chars = re.findall(r'星\s*5\s*共鳴者\s*[「『]([^」』]+)[」』]', seg)
        weapons = re.findall(r'星\s*5\s*武器\s*[「『]([^」』]+)[」』]', seg)
        print(f'BANNER {i}: {h.group(0)}')
        print('  HEADING_NAME:', repr(h.group(1)))
        print('  SECTION_CHARS:', repr(chars[:5]))
        print('  SECTION_WEAPONS:', repr(weapons[:5]))
        print('  PERIOD_MARKERS:', len(periods))
        for p in periods[:2]:
            print('  PERIOD_CONTEXT:', repr(seg[p.start():p.end()+120]))
        print('  SECTION_BEGIN:', repr(seg[:240]))
    print('DONE. No changes made.')

if __name__ == '__main__':
    main()
