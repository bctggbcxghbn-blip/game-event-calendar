"""Timezone presentation and final publication gate regressions (offline)."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import calendar_update_audit_v56 as quality

TIMEZONE_ASSERTIONS = r'''
const check=(value,message)=>{if(!value)throw Error(message)};
const base={id:'test',game:'endfield',name:'確認済み',kind:'イベント',start:'2026-11-05',end:null,start_time:'12:00'};
for(const [zone,clock] of [['UTC+8','13:00 JST'],['アジアサーバー時間（UTC+8）','13:00 JST'],['UTC','21:00 JST'],['JST','12:00 JST'],['Asia/Tokyo','12:00 JST'],['UTC+9','12:00 JST']]){
  const e={...base,time_zone:zone};const original=JSON.stringify(e);
  const view=calendarEvent(e);
  check(eventTime(view,'start')===clock,zone);
  check(calendarEvent(view)===view,'idempotent view');
  check(JSON.stringify(e)===original,'source mutation');
}
for(const zone of [undefined,'','サーバー時間','server (unverified)','America/Unknown']){
  const e={...base,time_zone:zone};check(eventTime(e,'start')==='12:00（タイムゾーン未確認）','unknown zone');
  check(calendarEvent(e).start===e.start,'unknown date');
}
const late={...base,start_time:'23:30',time_zone:'UTC+8'};
const lateView=calendarEvent(late);
check(lateView.start==='2026-11-06'&&lateView.end===null,'UTC8 next date');
check(eventTime(lateView,'start')==='00:30 JST','next date clock');
check(eventTime(calendarEvent(lateView),'start')==='00:30 JST','double conversion');
check(detailText({...lateView,displayStart:lateView.start,displayEnd:lateView.start}).includes('開始：2026-11-06 00:30 JST'),'detail next date');
start=lateView.start;
check(displayItems([lateView])[0].segments[0].displayEnd===lateView.start,'start marker date');
const prior=calendarEvent({...base,start_time:'00:30',time_zone:'UTC+10'});
check(prior.start==='2026-11-04'&&eventTime(prior,'start')==='23:30 JST','previous date');
const period=calendarEvent({...late,end:'2026-11-06',end_time:'23:59'});
check(period.start==='2026-11-06'&&period.end==='2026-11-07','both date boundaries');
for(const [stamp,day,clock] of [['2026-11-05T23:30:00+08:00','2026-11-06','00:30 JST'],['2026-11-05T18:30:00.123Z','2026-11-06','03:30 JST'],['2026-11-05T12:00:00+09:00','2026-11-05','12:00 JST']]){
  const e={...base,start_time:stamp,time_zone:'UTC+8'};
  check(calendarEvent(e).start===day&&eventTime(calendarEvent(e),'start')===clock,'explicit ISO offset');
}
const naive={...base,start_time:'2026-11-05T23:30:00'};
check(eventTime(naive,'start').includes('タイムゾーン未確認'),'naive timestamp');
check(eventTime({...base,start_time:undefined,start_label:'アップデート後'},'start')==='アップデート後','official label');
for(const game of ['genshin','wuwa','hsr','zzz','nte','arknights','endfield']){
  for(const kind of ['イベント','ガチャ']){
    const e={...base,game,kind,end:'2026-11-10',time_zone:'Asia/Tokyo'};
    const v=calendarEvent(e);start=v.start;
    check(v.start===e.start&&v.end===e.end,'existing dates');
    check(displayItems([v])[0].segments[0].displayEnd===e.end,'existing period');
  }
}
'''


class RuntimeTests(unittest.TestCase):
    def test_display_conversion_is_applied_when_loading(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('.map(calendarEvent);render()', html)

    def test_timezone_display_javascript(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node unavailable; assertions can also run in a JS runtime')
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        script = html.split('<script>')[1].split('let detailItems=')[0]
        bootstrap = 'global.document={getElementById:()=>({})};global.localStorage={getItem:()=>null};\n'
        subprocess.run([node, '-e', bootstrap + script + TIMEZONE_ASSERTIONS], check=True, capture_output=True, text=True)

    def test_workflow_final_gate_after_all_imports(self):
        workflow = (ROOT / '.github/workflows/update.yml').read_text(encoding='utf-8')
        gate = workflow.index('      - name: Audit calendar update quality V56 (read-only)')
        commit = workflow.index('      - name: Commit changes')
        for line in workflow[:commit].splitlines():
            if 'run: python ' in line and ('--apply' in line or any(script in line for script in (
                'update_events.py', 'import_v92.py', 'wiki_hsr_import.py', 'wiki_hsr_gacha.py',
                'hsr_official_asia_apply.py', 'hsr_official_import.py', 'hsr_maintenance_import.py'))):
                self.assertLess(workflow.index(line), gate, line)
        self.assertLess(gate, commit)
        self.assertLess(gate, workflow.index('      - name: Publish calendar Actions summary V58'))
        gate_block = workflow[gate:workflow.index('      - name:', gate + 10)]
        self.assertIn('calendar_update_audit_v56.py --strict', gate_block)
        self.assertNotIn('continue-on-error', gate_block)
        commit_block = workflow[commit:]
        self.assertNotIn('if: always()', commit_block)
        self.assertNotIn('continue-on-error', commit_block)

    def test_workflow_python_and_node_and_regressions(self):
        workflow = (ROOT / '.github/workflows/update.yml').read_text(encoding='utf-8')
        self.assertIn("python-version: '3.12'", workflow)
        self.assertIn("node-version: '22'", workflow)
        for name in ('test_endfield_unknown_end.py', 'test_calendar_runtime.py'):
            self.assertIn("-p '" + name + "'", workflow)
        self.assertLess(workflow.index('uses: actions/setup-node@'), workflow.index("-p 'test_endfield_unknown_end.py'"))

    def test_verification_workflow_cannot_publish(self):
        workflow = (ROOT / '.github/workflows/verify-calendar.yml').read_text(encoding='utf-8')
        self.assertIn("- 'codex/verify-calendar-*'", workflow)
        self.assertIn("if: startsWith(github.ref, 'refs/heads/codex/verify-calendar-')", workflow)
        self.assertIn('contents: read', workflow)
        self.assertIn('tools/verify_calendar.py --baseline origin/main', workflow)
        for forbidden in ('contents: write', 'git push', 'git commit', 'deploy-pages', '--apply', 'schedule:'):
            self.assertNotIn(forbidden, workflow)

    def test_final_gate_strict_rejects_bad_data_but_allows_markers(self):
        marker = dict(id='marker', game='endfield', name='確認済み', kind='イベント',
                      start='2026-11-05', end=None, source_status='公式開始日確認済み・終了日未定',
                      end_note='次回メンテナンス前', official_url='https://endfield.gryphline.com/ja-jp/news/1234')
        for invalid in (False, True):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                event = dict(marker, end='2026-02-30') if invalid else marker
                path = root / 'events.json'
                path.write_text(json.dumps([event]), encoding='utf-8')
                before = path.read_bytes()
                with patch.object(quality, 'ROOT', root), patch.object(quality, 'REPORT_DIR', root / 'reports'), patch.object(quality, 'load_previous', return_value=None), patch.object(sys, 'argv', ['audit', '--strict']):
                    if invalid:
                        with self.assertRaises(SystemExit) as raised:
                            quality.main()
                        self.assertEqual(raised.exception.code, 1)
                    else:
                        quality.main()
                self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
