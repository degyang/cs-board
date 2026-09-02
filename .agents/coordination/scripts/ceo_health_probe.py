#!/usr/bin/env python3
"""Short, deterministic CEO audit of goal alignment, bottlenecks and resources."""
from __future__ import annotations
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROW=re.compile(r"^\|\s*`?([^|`]+)`?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
OPEN={"READY","DISPATCHED","IN_PROGRESS","WORKING","TEST_READY","TESTING","PM_DECISION","CHANGES_REQUESTED","BLOCKED"}
def audit(root: Path):
 text=(root/'docs/agents/status.md').read_text(); goal=(root/'docs/agents/milestone-m1-manual-skills-closure.md').read_text()
 tasks=[]
 for line in text.splitlines():
  m=ROW.match(line)
  if m and m.group(1).strip() not in {'Task','---'}: tasks.append(dict(zip(('task_id','owner','status'),map(str.strip,m.groups()))))
 alerts=[]; active=[t for t in tasks if t['status'] in OPEN]
 for t in active:
  if t['status']=='BLOCKED': alerts.append({'kind':'blocked','task_id':t['task_id'],'message':'blocked task requires PM resolution plan'})
  if t['task_id'] not in goal and t['task_id'] not in {'CEO-RECOVERY-002'}: alerts.append({'kind':'goal-drift','task_id':t['task_id'],'message':'active PM work is not named in the stage-goal contract'})
 for suffix in ('WEB','CORE','MEDIA'):
  if any(t['owner']==f'WORKER_{suffix}' and t['status']=='READY' for t in active) and not any(t['owner']==f'WORKER_{suffix}' and t['status'] in OPEN-{'READY'} for t in active):
   alerts.append({'kind':'idle-capacity','owner':f'WORKER_{suffix}','message':'ready work and idle capacity coexist'})
 return {'checked_at':datetime.now(timezone.utc).isoformat(),'goal':'M1-MANUAL-SKILLS','alerts':alerts,'needs_pm':bool(alerts)}
if __name__=='__main__':
 root=Path(sys.argv[1]).resolve(); print(json.dumps(audit(root),ensure_ascii=False))
