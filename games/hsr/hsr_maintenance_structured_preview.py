#!/usr/bin/env python3
"""Read-only diagnostic of HSR HoYoLAB structured_content maintenance dates.

Does not modify any files. Does not change the existing automatic importer.
"""
import json
import re
from urllib.parse import urlencode

from hsr_maintenance_detail_probe import DETAIL, get_json, plain
from hsr_maintenance_time_preview import parse_window

POSTS = [('4.6', '46814308'), ('4.5', '46428208')]


def extract_structured(raw):
    if not isinstance(raw, str) or not raw.strip():
        return ''
    try:
        operations = json.loads(raw)
    except ValueError:
        return ''
    if not isinstance(operations, list):
        return ''
    chunks = []
    for op in operations:
        if not isinstance(op, dict):
            continue
        insert = op.get('insert')
        if isinstance(insert, str):
            chunks.append(insert)
        elif isinstance(insert, dict):
            # Embedded images/video are not text; do not infer dates from them.
            chunks.append(' ')
    return plain(' '.join(chunks))


def main():
    print('HSR structured_content maintenance preview — READ ONLY', flush=True)
    for version, pid in POSTS:
        print(f'\nVersion {version}: https://www.hoyolab.com/article/{pid}', flush=True)
        try:
            data = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
            outer = data.get('post', {}) if isinstance(data, dict) else {}
            post = outer.get('post', {}) if isinstance(outer, dict) else {}
            if not isinstance(post, dict):
                print('SKIP: Unexpected article structure', flush=True)
                continue
            text = extract_structured(post.get('structured_content'))
            print(f'Structured text length: {len(text)}', flush=True)
            for key in ('maintenance', 'update time', 'utc+8', 'utc +8'):
                match = re.search(re.escape(key), text, re.I)
                if match:
                    print(f'Context [{key}]: {text[max(0, match.start()-70):match.end()+180]}', flush=True)
            window, reason = parse_window(text)
            if window:
                start, end, hours = window
                print(f'PARSED: {start:%Y-%m-%d %H:%M} JST to {end:%Y-%m-%d %H:%M} JST (estimated {hours}h)', flush=True)
            else:
                print(f'NOT PARSED: {reason}', flush=True)
        except Exception as exc:
            print(f'WARNING: {type(exc).__name__}: {str(exc)[:150]}', flush=True)
    print('\nNo files modified.', flush=True)


if __name__ == '__main__':
    main()
