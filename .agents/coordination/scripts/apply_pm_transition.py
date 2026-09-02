#!/usr/bin/env python3
"""Apply mechanical PM handoff transitions; no acceptance decision is made here."""
from __future__ import annotations
import argparse, re
from pathlib import Path
ALLOWED={'record-test-ready':('DISPATCHED','TEST_READY'),'record-test-result':('TEST_READY','PM_DECISION')}
def replace_status(path:Path, task:str, old:str, new:str):
 text=path.read_text(); pattern=rf"(^\|\s*`{re.escape(task)}`\s*\|[^\n]*?\|\s*){old}(\s*\|)"
 changed,count=re.subn(pattern,rf"\g<1>{new}\2",text,count=1,flags=re.M)
 if count!=1: raise SystemExit(f'expected one {task} {old} row')
 path.write_text(changed)
def main():
 p=argparse.ArgumentParser(); p.add_argument('--project',type=Path,required=True); p.add_argument('--kind',choices=ALLOWED,required=True); p.add_argument('--task',required=True); a=p.parse_args(); old,new=ALLOWED[a.kind]
 replace_status(a.project/'docs/agents/status.md',a.task,old,new)
 contract=a.project/'docs/agents/tasks'/f'{a.task}.md'
 if contract.exists():
  text=contract.read_text(); text,count=re.subn(rf"(^- Status:\s*){old}$",rf"\g<1>{new}",text,count=1,flags=re.M)
  if count: contract.write_text(text)
if __name__=='__main__': main()
