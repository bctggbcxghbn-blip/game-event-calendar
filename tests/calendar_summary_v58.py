"""V58: read-only GitHub Actions summary for V56 and V57 reports."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / '.reports/calendar-v56/report.json'
MONITOR = ROOT / '.reports/calendar-v57/report.json'
OUTPUT = ROOT / '.reports/calendar-v58/summary.md'
GAMES = ('genshin', 'wuwa', 'hsr', 'zzz', 'nte', 'arknights', 'endfield')


def read_report(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def safe(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def build(quality, monitor):
    q = quality if isinstance(quality, dict) else {}
    m = monitor if isinstance(monitor, dict) else {}
    lines = ['## 📅 Calendar update summary V58', '',
             '| Check | Result |', '|---|---|',
             f"| V56 data quality | {safe(q.get('status', 'unavailable'))} |",
             f"| V57 update monitor | {safe(m.get('status', 'unavailable'))} |",
             f"| Total events | {safe(q.get('count', m.get('total', 'unknown')))} |",
             f"| Active today (V56) | {safe(q.get('active_today', 'unknown'))} |",
             f"| Quality critical / warnings | {len(q.get('critical', []))} / {len(q.get('warnings', []))} |",
             f"| Monitor critical / warnings | {len(m.get('critical', []))} / {len(m.get('warnings', []))} |",
             '', '### Game counts', '', '| Game | Events |', '|---|---:|']
    counts = q.get('counts_by_game') or m.get('counts_by_game') or {}
    for game in GAMES:
        lines.append(f'| {game} | {safe(counts.get(game, 0))} |')
    for game in sorted(set(counts) - set(GAMES)):
        lines.append(f'| {safe(game)} | {safe(counts[game])} |')
    changes = q.get('changes', {})
    lines.extend(['', '### Changes since Git HEAD', '',
                  f"Added: **{safe(changes.get('added', 'unknown'))}** · Removed: **{safe(changes.get('removed', 'unknown'))}** · Modified: **{safe(changes.get('modified', 'unknown'))}**",
                  ''])
    if not q.get('change_comparison_available', False):
        lines.append('Comparison baseline unavailable; changes shown as unknown.')
    issues = [('V56 critical', x) for x in q.get('critical', [])] + [('V56 warning', x) for x in q.get('warnings', [])] + [('V57 critical', x) for x in m.get('critical', [])] + [('V57 warning', x) for x in m.get('warnings', [])]
    lines.extend(['', '### Alerts', ''])
    if issues:
        for label, issue in issues[:20]:
            lines.append(f'- **{label}:** {safe(json.dumps(issue, ensure_ascii=False))}')
        if len(issues) > 20:
            lines.append(f'- …and {len(issues) - 20} more (see report artifacts)')
    else:
        lines.append('No reported alerts.' if quality is not None and monitor is not None else 'Some source reports are missing; check earlier steps and artifacts.')
    lines.extend(['', '> Read-only summary. V56/V57 reports are the source of truth; this step never modifies events.json.', ''])
    return '\n'.join(lines)


def main():
    quality, monitor = read_report(QUALITY), read_report(MONITOR)
    summary = build(quality, monitor)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(summary, encoding='utf-8')
    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a', encoding='utf-8') as f:
            f.write(summary + '\n')
    print('V58 SUMMARY WRITTEN:', OUTPUT.relative_to(ROOT))
    print('QUALITY:', quality.get('status') if quality else 'missing', 'MONITOR:', monitor.get('status') if monitor else 'missing')
    print('EVENTS_JSON_UNCHANGED')


if __name__ == '__main__':
    main()
