#!/usr/bin/env python3
"""Apply mechanical PM handoff transitions; no acceptance decision is made here."""
from __future__ import annotations
import argparse, re
from pathlib import Path
ALLOWED={
 'record-test-ready':('DISPATCHED','TEST_READY'),
 'record-test-result':('TEST_READY','PM_DECISION'),
 'recover-delivery':('BLOCKED','TEST_READY'),
 'recover-dispatch':('BLOCKED','DISPATCHED'),
}
def replace_status(path:Path, task:str, old:str, new:str):
 text=path.read_text(); pattern=rf"(^\|\s*`{re.escape(task)}`\s*\|[^\n]*?\|\s*){old}(\s*\|)"
 changed,count=re.subn(pattern,rf"\g<1>{new}\2",text,count=1,flags=re.M)
 if count!=1: raise SystemExit(f'expected one {task} {old} row')
 path.write_text(changed)
def replace_delivery(path:Path, task:str, delivery:str):
 lines=path.read_text().splitlines()
 changed=0
 for index,line in enumerate(lines):
  columns=[value.strip() for value in line.split('|')[1:-1]]
  if len(columns)>=6 and columns[0].strip('`')==task:
   columns[4]=f'`{delivery}`'
   columns[5]='Tester pending'
   lines[index]='| '+' | '.join(columns)+' |'; changed+=1
 if changed!=1: raise SystemExit(f'expected one {task} row for delivery')
 path.write_text('\n'.join(lines)+'\n')
def main():
 p=argparse.ArgumentParser(); p.add_argument('--project',type=Path,required=True); p.add_argument('--kind',choices=ALLOWED,required=True); p.add_argument('--task',required=True); p.add_argument('--delivery'); a=p.parse_args(); old,new=ALLOWED[a.kind]
 status_path=a.project/'docs/agents/status.md'
 replace_status(status_path,a.task,old,new)
 if a.kind=='recover-delivery':
  if not a.delivery: p.error('recover-delivery requires --delivery')
  replace_delivery(status_path,a.task,a.delivery)
 contract=a.project/'docs/agents/tasks'/f'{a.task}.md'
 if contract.exists():
  text=contract.read_text(); text,count=re.subn(rf"(^- Status:\s*){old}$",rf"\g<1>{new}",text,count=1,flags=re.M)
  if count: contract.write_text(text)
if __name__=='__main__': main()
