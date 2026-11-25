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
    named = candidate.get('version_kind') == 'named'
    if named:
        if candidate.get('game') != 'endfield' or candidate.get('status') not in ('scheduled', 'released_candidate'):
            return None
        if not str(candidate.get('release_name') or '').strip() or not candidate.get('announced_release_date'):
            return None
    elif candidate.get('status') != 'official' or not version_key(candidate.get('version')):
        return None
    if not valid_url(candidate.get('official_url')) or candidate.get('region') != 'JP':
        return None
    effective = parse_date(candidate.get('effective_from'))
    checked = parse_date(candidate.get('checked_at'))
    expires = parse_date(candidate.get('expires_at')) if candidate.get('expires_at') else None
    if (not named and not effective) or not checked or checked > today or (effective and effective > today) or (expires and today >= expires):
        return None
    fields = ('version', 'release_name', 'version_kind', 'status', 'official_url', 'checked_at',
              'effective_from', 'expires_at', 'region', 'announced_release_date',
              'source_cids', 'evidence_urls')
    result = {key: candidate.get(key) for key in fields}
    return result


def endfield_candidate_from_audit(report, today=None):
    """Convert the audit's latest released named candidate without guessing."""
    today = today or dt.date.today()
    groups = report.get('named_version_groups') if isinstance(report, dict) else None
    if not isinstance(groups, list):
        return []
    candidates = []
    for group in groups:
        item = group.get('latest_released_candidate') if isinstance(group, dict) else None
        if not isinstance(item, dict) or not item.get('named_version'):
            continue
        release_date = parse_date(item.get('announced_release_date'))
        if not release_date or release_date > today or not item.get('article_url'):
            continue
        evidence = [e for e in group.get('evidence', []) if isinstance(e, dict)]
        cids = [str(e['cid']) for e in evidence if str(e.get('cid', '')).isdigit()]
        urls = [e.get('article_url') for e in evidence if valid_url(e.get('article_url'))]
        candidates.append({'game': 'endfield', 'version': None,
                          'release_name': group['named_version'], 'version_kind': 'named',
                          'status': 'released_candidate', 'official_url': item['article_url'],
                          'checked_at': report.get('checked_at'), 'effective_from': None,
                          'expires_at': None, 'region': 'JP',
                          'announced_release_date': release_date.isoformat(),
                          'source_cids': sorted(set(cids)), 'evidence_urls': sorted(set(urls))})
    return candidates


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
        if item.get('version_kind') == 'named':
            old_date = parse_date(old.get('announced_release_date'))
            new_date = parse_date(item.get('announced_release_date'))
            if old.get('version_kind') == 'named' and old_date and new_date and new_date < old_date:
                continue
            result[game] = item
            continue
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
    parser.add_argument('--discover-endfield', action='store_true',
                        help='read the official Endfield audit and merge named candidates')
    parser.add_argument('--dry-run', action='store_true',
                        help='validate and print the merge without writing')
    args = parser.parse_args()
    if args.discover_endfield:
        from tools.verify_endfield_api import audit
        existing = json.loads(args.path.read_text(encoding='utf-8'))
        candidates = endfield_candidate_from_audit(audit())
        result = merge(existing, candidates)
        print(json.dumps({'candidates': candidates, 'changed': result != existing}, ensure_ascii=False))
        if args.dry_run:
            return 0
        args.path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return 0
    return 0 if update(args.path, args.candidates) else 1


if __name__ == '__main__':
    raise SystemExit(main())
