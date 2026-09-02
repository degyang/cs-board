from __future__ import annotations
import json, subprocess, tempfile, unittest
from pathlib import Path
PROBE=Path(__file__).parents[1]/'ceo_health_probe.py'
class CEOHealthProbeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); (self.root/'docs/agents').mkdir(parents=True)
 def tearDown(self): self.tmp.cleanup()
 def audit(self, rows, goal):
  (self.root/'docs/agents/status.md').write_text('| Task | Owner | Status | Contract | Delivery | Review |\n| --- | --- | --- | --- | --- | --- |\n'+'\n'.join(rows))
  (self.root/'docs/agents/milestone-m1-manual-skills-closure.md').write_text(goal)
  return json.loads(subprocess.check_output(['python3',str(PROBE),str(self.root)],text=True))
 def test_flags_blocker_and_goal_drift(self):
  data=self.audit(['| `MEDIA-1` | WORKER_MEDIA | BLOCKED | x | y | z |','| `SIDE-1` | WORKER_WEB | READY | x | y | z |'],'MEDIA-1')
  self.assertEqual({x['kind'] for x in data['alerts']},{'blocked','goal-drift','idle-capacity'})
 def test_accepts_goal_aligned_work(self):
  self.assertFalse(self.audit(['| `WEB-1` | WORKER_WEB | TEST_READY | x | y | z |'],'WEB-1')['needs_pm'])
 def test_flags_pm_stalled_after_two_failed_unchanged_cycles(self):
  rows=['| `CORE-1` | WORKER_CORE | BLOCKED | x | pending | waiting |']
  first=self.audit(rows,'CORE-1')
  self.assertEqual(first['unchanged_cycles'],1)
  runtime=self.root/'.agents/coordination/runtime'
  (runtime/'pm-scheduler.json').write_text(json.dumps({'state':'incomplete'}))
  second=self.audit(rows,'CORE-1')
  self.assertEqual(second['unchanged_cycles'],2)
  self.assertIn('pm-stalled',{item['kind'] for item in second['alerts']})
 def test_progress_resets_when_actionable_state_changes(self):
  self.audit(['| `CORE-1` | WORKER_CORE | BLOCKED | x | pending | waiting |'],'CORE-1')
  changed=self.audit(['| `WEB-1` | WORKER_WEB | READY | x | pending | waiting |'],'CORE-1')
  self.assertEqual(changed['unchanged_cycles'],1)
if __name__=='__main__': unittest.main()
