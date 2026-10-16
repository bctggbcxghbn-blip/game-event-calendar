#!/usr/bin/env python3
"""Read-only HoYoLAB post structure diagnostic for HSR maintenance notices.

Prints only field names, value types, lengths and short sanitized previews.
Never writes repository files or changes calendar events.
"""
import json
import re
from urllib.parse import urlencode
from hsr_maintenance_detail_probe import DETAIL, get_json

POST_IDS = ('46814308', '46428208')  # Version 4.6 and 4.5
MAX_PREVIEW = 180


def shape(value):
    if isinstance(value, str):
        return f'str, {len(value)} chars'
    if isinstance(value, list):
        return f'list, {len(value)} items'
    if isinstance(value, dict):
        return f'dict, {len(value)} keys'
    return type(value).__name__


def inspect(value, path='data', depth=0):
    if depth > 3:
        return
    if isinstance(value, dict):
        for key, item in list(value.items())[:35]:
            if not isinstance(key, str):
                continue
            # Do not print user IDs, cookies, tokens, etc.
            if re.search(r'uid|user|author|cookie|token|secret|auth|device|session', key, re.I):
                continue
            loc = f'{path}.{key}'
            print(f'  {loc}: {shape(item)}', flush=True)
            if isinstance(item, dict) and (depth < 2 or key in ('post', 'content', 'structured_content')):
                inspect(item, loc, depth + 1)
            elif isinstance(item, str) and key in ('content', 'structured_content', 'post', 'subject'):
                # Only preview structure, not full article or arbitrary metadata.
                print(f'    preview: {item[:MAX_PREVIEW]!r}', flush=True)
                if item.lstrip().startswith(('{', '[')):
                    try:
                        decoded = json.loads(item)
                        print(f'    decoded JSON: {shape(decoded)}', flush=True)
                        if isinstance(decoded, dict):
                            inspect(decoded, loc + '(json)', depth + 1)
                    except (ValueError, TypeError):
                        pass
    elif isinstance(value, list):
        print(f'  {path}: list of {len(value)} items', flush=True)
        if value and isinstance(value[0], dict):
            inspect(value[0], path + '[0]', depth + 1)


def main():
    print('HSR official article structure diagnostic — READ ONLY', flush=True)
    for pid in POST_IDS:
        print(f'\nARTICLE: https://www.hoyolab.com/article/{pid}', flush=True)
        try:
            data = get_json(DETAIL + '?' + urlencode({'post_id': pid}))
            print(f'Data: {shape(data)}', flush=True)
            inspect(data)
        except Exception as exc:
            print(f'WARNING: {type(exc).__name__}: {str(exc)[:160]}', flush=True)
    print('\nDiagnostic complete. No files modified.', flush=True)


if __name__ == '__main__':
    main()
