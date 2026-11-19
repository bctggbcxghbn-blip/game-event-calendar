"""Safely merge explicitly verified official Japanese version candidates.

This module is intentionally offline by default. Discovery adapters may supply
candidates, but no candidate is accepted without an official URL, effective
date, JP region, and a non-future effective date.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

GAMES = ('genshin', 'wuwa', 'hsr', 'zzz', 'nte', 'arknights', 'endfield')


def version_key(value):
    try:
        return tuple(int(part) for part in str(value).lstrip('vV').split('.'))
    except (TypeError, ValueError):
        return ()


def valid_url(value):
    parsed = urlparse(str(value or ''))
    return parsed.scheme == 'https' and bool(parsed.netloc)


def parse_date(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace('Z', '+00:00')).date()
    except (TypeError, ValueError):
        return None


def accept(candidate, today=None):
    """Return a normalized official candidate, or None when unsafe."""
    today = today or dt.date.today()
    if not isinstance(candidate, dict) or candidate.get('game') not in GAMES:
        return None
    if candidate.get('status') != 'official' or not version_key(candidate.get('version')):
        return None
    if not valid_url(candidate.get('official_url')) or candidate.get('region') != 'JP':
        return None
    effective = parse_date(candidate.get('effective_from'))
    checked = parse_date(candidate.get('checked_at'))
    expires = parse_date(candidate.get('expires_at')) if candidate.get('expires_at') else None
    if not effective or not checked or checked > today or effective > today or (expires and today >= expires):
        return None
    result = {key: candidate.get(key) for key in ('version', 'status', 'official_url', 'checked_at', 'effective_from', 'expires_at', 'region')}
    return result


def merge(existing, candidates, today=None):
    """Merge accepted candidates without erasing confirmed data on failures."""
    today = today or dt.date.today()
    if not isinstance(existing, dict):
        raise ValueError('versions data must be an object')
    result = {game: dict(existing.get(game) or {}) for game in GAMES}
    for candidate in candidates or ():
        item = accept(candidate, today=today)
        if not item:
            continue
        game = candidate['game']
        old = result[game]
        old_key = version_key(old.get('version')) if old.get('status') == 'official' else ()
        if old_key and version_key(item['version']) < old_key:
            continue
        result[game] = item
    return result


def update(path, candidates_path=None, today=None):
    """Update a JSON file from a local candidate snapshot; failures preserve it."""
    path = Path(path)
    try:
        existing = json.loads(path.read_text(encoding='utf-8'))
        candidates = json.loads(Path(candidates_path).read_text(encoding='utf-8')) if candidates_path else []
        result = merge(existing, candidates, today=today)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', type=Path, default=Path('versions_ja.json'))
    parser.add_argument('--candidates', type=Path)
    args = parser.parse_args()
    return 0 if update(args.path, args.candidates) else 1


if __name__ == '__main__':
    raise SystemExit(main())
