#!/usr/bin/env python3
"""V44: run V43, write GitHub step summary + structured monitoring report.
V43 remains the source of truth for parsing, rate limits, and imports.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent


def parse_log(log, returncode):
    def last(pattern, default=None):
        matches = list(re.finditer(pattern, log, re.MULTILINE))
        return matches[-1].group(1) if matches else default
    summary = re.findall(r'^SUMMARY: INDEX_OK=(\d+) DISCOVERED=(\d+) READY=(\d+) BEFORE=(\d+) AFTER=(\d+) MODE=(\w+)', log, re.MULTILINE)
    result = {
        'status': 'ok' if returncode == 0 and summary else 'failed',
        'exit_code': returncode,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'latest_priority': last(r'^PRIORITY_LATEST: (.+)$', ''),
        'next_probe': last(r'^NEXT_PROBE (.+)$', ''),
        'cache_hits': len(re.findall(r'^(?:INDEX_OK|READY) .*CACHE_HIT', log, re.MULTILINE)),
        'rate_limits': len(re.findall(r'^RATE_LIMIT HTTP_429', log, re.MULTILINE)),
        'manual_holds': len(re.findall(r'^HOLD SHORT_NAME_REVIEW', log, re.MULTILINE)),
        'candidate_total': sum(map(int, re.findall(r'^SUMMARY: BEFORE=\d+ UNIQUE=\d+ CANDIDATE=(\d+)', log, re.MULTILINE))),
        'errors': [line for line in log.splitlines() if line.startswith(('STOP ', 'ERROR '))][:20],
    }
    if summary:
        indexes, discovered, ready, before, after, mode = summary[-1]
        result.update(indexes_ok=int(indexes), versions_discovered=int(discovered), versions_ready=int(ready), before=int(before), after=int(after), added=int(after)-int(before), mode=mode)
    else:
        result['errors'].append('V43 completion summary missing')
    return result


def markdown(result):
    status = '成功' if result['status'] == 'ok' else '失敗（要確認）'
    lines = ['## 鳴潮Wiki 自動更新 V44', '', f'**状態:** {status}', '',
             '| 項目 | 結果 |', '|---|---|',
             f"| イベント件数 | {result.get('before', '不明')} → {result.get('after', '不明')} |",
             f"| 新規追加 | {result.get('added', '不明')} |",
             f"| 新規候補 | {result['candidate_total']} |",
             f"| 確認待ち | {result['manual_holds']} |",
             f"| 取得成功バージョン | {result.get('versions_ready', '不明')} |",
             f"| キャッシュヒット | {result['cache_hits']} |",
             f"| HTTP 429 | {result['rate_limits']} |",
             f"| 次バージョン検査 | {result['next_probe'] or '記録なし'} |",
             f"| 優先バージョン | {result['latest_priority'] or '不明'} |", '']
    if result['errors']:
        lines.extend(['### エラー', ''] + ['- '+e for e in result['errors']])
    if result['manual_holds']:
        lines.extend(['', '確認待ちの名前が残っています。自動登録はしません。'])
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    p.add_argument('--events', default='events.json')
    p.add_argument('--report-dir', default='.reports/wuwa-v44')
    args, passthrough = p.parse_known_args()
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(HERE/'wuwa_wiki_auto_runner_v43.py'), '--events', args.events]
    if args.apply:
        command.append('--apply')
    command.extend(passthrough)
    print('WUWA V44 MONITORED RUNNER MODE=' + ('APPLY' if args.apply else 'DRY_RUN'), flush=True)
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', check=False)
        log, rc = proc.stdout, proc.returncode
    except OSError as exc:
        log, rc = 'ERROR START '+repr(exc)+'\n', 2
    print(log, end='' if log.endswith('\n') else '\n', flush=True)
    report = parse_log(log, rc)
    (report_dir/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    md = markdown(report)
    (report_dir/'summary.md').write_text(md, encoding='utf-8')
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a', encoding='utf-8') as f:
            f.write(md)
    print('V44_REPORT', report_dir/'report.json', 'STATUS='+report['status'], flush=True)
    return rc if rc else (0 if report['status'] == 'ok' else 5)

if __name__ == '__main__':
    sys.exit(main())
