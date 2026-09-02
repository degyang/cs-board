from __future__ import annotations
import json, os, subprocess, tempfile, unittest
from pathlib import Path
SOURCE=Path(__file__).parents[1]
class TesterDispatchTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); (self.root/'.agents/coordination/runtime').mkdir(parents=True); (self.root/'docs/agents/tasks').mkdir(parents=True)
  (self.root/'.agents/coordination/agents.json').write_text(json.dumps({'agents':{'TESTER_WEB':{'domain':'web','worktree':str(self.root),'model':'terra','reasoning_effort':'medium'},'WORKER_WEB':{}}}))
  (self.root/'docs/agents/status.md').write_text('| Task | Owner | Status | Contract | Delivery | Review |\n| --- | --- | --- | --- | --- | --- |\n| `WEB-1` | WORKER_WEB | TEST_READY | `docs/agents/tasks/WEB-1.md` | abc | pending |\n')
  (self.root/'docs/agents/tasks/WEB-1.md').write_text('# task\n'); self.bin=self.root/'bin'; self.bin.mkdir(); self.calls=self.root/'calls'; self.active=self.root/'active'
  for name,body in {'systemctl':f"[ -f '{self.active}' ]",'systemd-run':f"printf '%s\\n' \"$*\" > '{self.calls}'\ntouch '{self.active}'"}.items():
   p=self.bin/name; p.write_text('#!/bin/sh\n'+body+'\n'); p.chmod(0o755)
 def tearDown(self): self.tmp.cleanup()
 def test_routes_web_delivery_to_web_tester(self):
  env={**os.environ,'SYSTEMCTL_BIN':str(self.bin/'systemctl'),'SYSTEMD_RUN_BIN':str(self.bin/'systemd-run')}
  result=subprocess.run(['bash',str(SOURCE/'dispatch_test_agent.sh'),str(self.root)],env=env,capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr); call=self.calls.read_text(); self.assertIn('TESTER_WEB',call); self.assertIn('WEB-1',call); self.assertIn('run_test_agent.sh',call)
 def test_does_not_repeat_completed_delivery(self):
  (self.root/'.agents/coordination/runtime/test-completed-WEB-1.json').write_text(json.dumps({'state':'completed','delivery':'abc'}))
  env={**os.environ,'SYSTEMCTL_BIN':str(self.bin/'systemctl'),'SYSTEMD_RUN_BIN':str(self.bin/'systemd-run')}
  result=subprocess.run(['bash',str(SOURCE/'dispatch_test_agent.sh'),str(self.root)],env=env,capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr); self.assertFalse(self.calls.exists())
if __name__=='__main__': unittest.main()
