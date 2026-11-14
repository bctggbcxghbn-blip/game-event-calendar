"""Offline verification only: never import live events, commit, push or publish."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from calendar_quality_v47 import analyze
from calendar_update_audit_v56 import audit
from calendar_update_monitor_v57 import assess


def digest(data):
    return hashlib.sha256(data).hexdigest()


def css(data):
    return re.search(rb'<style>(.*?)</style>', data, re.S).group(1).replace(b'\r\n', b'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', help='Git ref used to check data and CSS preservation')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = {name: (ROOT / name).read_bytes() for name in ('events.json', 'labels_ja.json', 'index.html')}
    report = {'python': sys.version.split()[0], 'node_available': bool(shutil.which('node')), 'suites': [], 'errors': []}
    if not report['node_available']:
        report['errors'].append('Node is required: JavaScript tests must not be skipped')
    if args.baseline:
        for name in before:
            result = subprocess.run(['git', 'show', f'{args.baseline}:{name}'], cwd=ROOT, capture_output=True)
            if result.returncode:
                report['errors'].append(f'Cannot read baseline: {name}')
            elif (css(result.stdout) != css(before[name]) if name == 'index.html' else
                  result.stdout.replace(b'\r\n', b'\n') != before[name].replace(b'\r\n', b'\n')):
                report['errors'].append(f'Protected content differs from baseline: {name}')
    env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    for folder in ('tests', 'games/wuwa', 'games/hsr'):
        bootstrap = (
            "import sys,unittest; "
            f"sys.path[:0]=[{str(ROOT)!r},{str(ROOT / folder)!r}]; "
            f"r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover({folder!r})); "
            "sys.exit(not r.wasSuccessful() or bool(r.skipped))"
        )
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', bootstrap], cwd=ROOT, env=env)
        report['suites'].append({'folder': folder, 'exit_code': result.returncode})
        if result.returncode:
            report['errors'].append(f'Tests failed or skipped: {folder}')
    events = json.loads(before['events.json'])
    report['quality'] = audit(events)
    report['monitor'] = assess(events)
    report['source_quality'] = analyze(events, json.loads(before['labels_ja.json']))
    if report['quality']['critical'] or any(i['level'] == 'error' for i in report['source_quality']['issues']):
        report['errors'].append('Calendar quality audit failed')
    report['preserved'] = {name: (ROOT / name).read_bytes() == data for name, data in before.items()}
    report['events_sha256'] = digest(before['events.json'])
    if not all(report['preserved'].values()):
        report['errors'].append('Protected files changed during verification')
    report['status'] = 'failed' if report['errors'] else 'passed'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('status', 'errors', 'preserved', 'events_sha256')}, ensure_ascii=False))
    return int(bool(report['errors']))


if __name__ == '__main__':
    sys.exit(main())
