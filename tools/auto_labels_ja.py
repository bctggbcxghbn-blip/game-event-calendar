"""Apply evidence-backed Japanese name pairs; never translate or alter event dates."""
import argparse
import copy
import csv
import datetime as dt
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GAMES = {'genshin', 'wuwa', 'hsr', 'zzz', 'nte', 'arknights', 'endfield'}
JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
EN = re.compile(r'[A-Za-z]{3,}')
OFFICIAL = {
    'genshin': {'genshin.hoyoverse.com', 'www.hoyolab.com', 'hoyolab.com'},
    'hsr': {'hsr.hoyoverse.com', 'www.hoyolab.com', 'hoyolab.com'},
    'zzz': {'zenless.hoyoverse.com', 'www.hoyolab.com', 'hoyolab.com'},
    'wuwa': {'wutheringwaves.kurogames.com'},
    'nte': {'nte.perfectworld.com'},
    'arknights': {'www.arknights.jp', 'arknights.jp'},
    'endfield': {'endfield.gryphline.com'},
}
WIKI = {'genshin': 'genshinwiki', 'hsr': 'star-rail', 'wuwa': 'w-w', 'zzz': 'zenless'}
LOCALIZATION = {'genshin': 'genshin-impact.fandom.com', 'hsr': 'honkai-star-rail.fandom.com',
                'zzz': 'zenless-zone-zero.fandom.com', 'wuwa': 'wutheringwaves.fandom.com'}


def trusted_source(game, url, source_type):
    try:
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port:
            return False
        if source_type == 'official':
            return parsed.hostname in OFFICIAL.get(game, set())
        if source_type == 'jp_wiki':
            return (parsed.hostname == 'wikiwiki.jp' and game in WIKI
                    and unquote(parsed.path).startswith('/' + WIKI[game] + '/'))
        if source_type == 'localization_index':
            return parsed.hostname == LOCALIZATION.get(game) and parsed.path.startswith('/wiki/')
    except (TypeError, ValueError):
        pass
    return False


def valid_pair(pair):
    if not isinstance(pair, dict):
        return False
    if any(not isinstance(pair.get(k), str) or not pair[k].strip()
           for k in ('game', 'english_name', 'japanese_name', 'source_url', 'source_type', 'reviewed_on')):
        return False
    if pair['game'] not in GAMES or not EN.search(pair['english_name']) or JP.search(pair['english_name']):
        return False
    if not JP.search(pair['japanese_name']) or len(pair['japanese_name']) > 180:
        return False
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', pair['reviewed_on']):
        return False
    try:
        reviewed = dt.date.fromisoformat(pair['reviewed_on'])
        if reviewed > dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date():
            return False
    except ValueError:
        return False
    return trusted_source(pair['game'], pair['source_url'], pair['source_type'])


def reviewed_pairs(root):
    pairs = []
    for path in sorted((root / 'reviews').glob('*_verified_translations.csv')):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                pairs.append({**row, 'evidence_file': path.relative_to(root).as_posix()})
    return pairs


def source_pairs(events):
    """Only existing bilingual records from official/Japanese Wiki importers qualify."""
    result = []
    for e in events:
        original, name = e.get('original_name'), e.get('name')
        if not isinstance(original, str) or not isinstance(name, str) or not JP.search(name):
            continue
        status = str(e.get('source_status', ''))
        source_type = 'jp_wiki' if status.startswith('日本語Wiki') else 'official' if ('公式' in status and '要確認' not in status and '未確認' not in status) else None
        if source_type is None:
            continue
        url = e.get('official_url') or e.get('url')
        pair = dict(game=e.get('game'), english_name=original, japanese_name=name,
                    source_url=url, source_type=source_type,
                    reviewed_on=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat(),
                    evidence_event_id=e.get('id'), evidence_kind='source_record_pair')
        if valid_pair(pair):
            result.append(pair)
    return result


def title_key(name):
    # Explicit announcement wrapper only; no fuzzy/partial/date-based matching.
    match = re.fullmatch(r'["“](.+)["”] Event Details', name)
    return match.group(1) if match else name


def reconcile(events, labels, pairs):
    if not isinstance(events, list) or not all(isinstance(e, dict) for e in events) or not isinstance(labels, dict):
        raise ValueError('Invalid events/labels structure')
    index = {}
    rejected = []
    for pair in list(pairs) + source_pairs(events):
        if not valid_pair(pair):
            rejected.append({'game': pair.get('game'), 'english_name': pair.get('english_name'), 'reason': 'invalid_evidence'})
            continue
        index.setdefault((pair['game'], pair['english_name']), []).append(pair)
    updated = copy.deepcopy(labels)
    applied, pending, conflicts = [], [], []
    names = sorted({(e.get('game'), name) for e in events for name in (e.get('original_name'), e.get('name'))
                    if e.get('game') in GAMES and isinstance(name, str) and EN.search(name) and not JP.search(name)})
    for game, name in names:
        matches = index.get((game, name), []) or index.get((game, title_key(name)), [])
        translations = {p['japanese_name'] for p in matches}
        existing = updated.get(game, {}).get(name, {})
        current = existing.get('name') if isinstance(existing, dict) else None
        if len(translations) > 1 or (translations and current and current not in translations):
            conflicts.append({'game': game, 'english_name': name, 'reason': 'conflicting_names'})
            continue
        if current:
            continue
        if not translations:
            pending.append({'game': game, 'english_name': name, 'reason': 'no_verified_pair'})
            continue
        japanese = next(iter(translations))
        updated.setdefault(game, {})[name] = {'name': japanese}
        applied.append({'game': game, 'english_name': name, 'japanese_name': japanese,
                        'matching': 'exact' if title_key(name) == name else 'explicit_event_details_wrapper',
                        'sources': matches})
    return updated, {'applied': applied, 'pending': pending, 'conflicts': conflicts, 'rejected': rejected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    event_path, label_path = root / 'events.json', root / 'labels_ja.json'
    original_events = event_path.read_bytes()
    events, labels = json.loads(original_events), json.loads(label_path.read_bytes())
    updated, report = reconcile(events, labels, reviewed_pairs(root))
    report['mode'] = 'apply' if args.apply else 'preview'
    evidence_path = root / 'reviews/auto_labels_ja_evidence.json'
    history = json.loads(evidence_path.read_bytes()) if evidence_path.exists() else {'version': 1, 'entries': []}
    if args.apply and report['applied']:
        history['entries'].extend(report['applied'])
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        label_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if event_path.read_bytes() != original_events:
        raise RuntimeError('events.json changed unexpectedly')
    output = root / '.reports/auto-labels-ja/report.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Japanese labels: {report['mode']} added={len(report['applied'])} pending={len(report['pending'])} conflicts={len(report['conflicts'])} rejected={len(report['rejected'])}; events.json untouched")
    return 0


if __name__ == '__main__':
    sys.exit(main())
