#!/usr/bin/env python3
"""V46: tolerate only verified rate-limited, no-write V44 aborts."""
import json
from pathlib import Path
import subprocess
import sys

REPORT = Path('.reports/wuwa-v44/report.json')

def safe_rate_limit_abort(returncode, report, log):
    if returncode == 0 or not isinstance(report, dict):
        return False
    errors = report.get('errors', [])
    return (report.get('status') == 'failed'
            and report.get('exit_code') == returncode
            and report.get('rate_limits', 0) > 0
            and any('HTTP_429' in str(e) for e in errors)
            and 'NO_WRITES' in log
            and any(marker in log for marker in ('STOP_VERSION_ERROR', 'STOP_INDEX_ERROR'))
            and 'HTTP_429' in log)

def main():
    command = [sys.executable, 'games/wuwa/wuwa_wiki_auto_runner_v44.py', '--apply']
    # Preserve full V44 output for debugging; no new HTTP requests.
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors='replace', check=False)
    log = proc.stdout
    print(log, end='' if log.endswith('\n') else '\n', flush=True)
    try:
        report = json.loads(REPORT.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        report = None
    if safe_rate_limit_abort(proc.returncode, report, log):
        print('::warning title=Wuwa Wiki HTTP 429::V44 stopped without writes; continuing other game updates. See wuwa-v44 report.', flush=True)
        return 0
    return proc.returncode

if __name__ == '__main__':
    sys.exit(main())
