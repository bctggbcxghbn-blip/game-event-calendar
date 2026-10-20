#!/usr/bin/env python3
"""V69: read-only review of NTE V68 candidate report."""
import json
from pathlib import Path

def main():
    p = Path(__file__).resolve().parents[2] / 'reports' / 'nte-v69-review.json'
    report = json.loads(p.read_text(encoding='utf-8'))
    print(f"NTE {report['version']}: {report['candidate_count']} candidate lines; {len(report['reviewed_event_candidates'])} dated event leads; imported=0")
    for event in report['reviewed_event_candidates']:
        print(f"REVIEW {event['name']}: {event['start']} -> {event['end']} ({event['timezone']})")

if __name__ == '__main__':
    main()
