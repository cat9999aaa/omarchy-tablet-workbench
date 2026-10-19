#!/usr/bin/python3
"""Fixed read-only task-center requests. No raw source or exception output."""
import json,math,os,signal,sys,time,re
from pathlib import Path
from navigation_read import ReadBudget,ReadError
from task_model import TaskDataError,project_path
from task_source import collect_snapshot,collect_detail,handoff,finish

def configuration():
 base=Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
 if not base.is_absolute():raise TaskDataError('invalid-project')
 path=base/'omarchy-tablet-workbench/task-center.json'
 try:
  if path.is_symlink() or path.parent.is_symlink():raise TaskDataError('invalid-project')
  with path.open('rb') as f:raw=f.read(8193)
  if len(raw)>8192:raise TaskDataError('invalid-project')
  value=json.loads(raw)
  if not isinstance(value,dict) or set(value)!=set(('schema','project_root')) or type(value['schema']) is not int or value['schema']!=1:raise TaskDataError('invalid-project')
  return project_path(value['project_root'])
 except (OSError,ValueError,TypeError):raise TaskDataError('invalid-project') from None

def request(command,value):
 if not isinstance(value,dict):raise ReadError('invalid-request')
 keys={'snapshot':{'generation'},'detail':{'generation','agent_id','remaining_ms','output','scope'},'action':{'action','output'},'guard':{'output'}}
 if command not in keys or set(value)!=keys[command]:raise ReadError('invalid-request')
 if command not in ('action','guard') and (type(value['generation']) is not int or not 0<=value['generation']<=2147483647):raise ReadError('invalid-request')
 if command!='snapshot':
  output=value.get('output')
  if not isinstance(output,str) or not output.strip() or len(output)>256 or any(ord(c)<32 or ord(c)==127 for c in output):raise ReadError('invalid-request')
 remaining=value.get('remaining_ms',5000)
 if type(remaining) is not int or not 1<=remaining<=5000:raise ReadError('invalid-request')
 budget=ReadBudget(remaining/1000 if command!='guard' else 1,max_read_seconds=2)
 if command=='detail' and (not isinstance(value['scope'],str) or re.fullmatch('[0-9a-f]{64}',value['scope']) is None):raise ReadError('invalid-request')
 if command=='guard':return finish(budget,value['output'])
 if command=='action':return handoff(value['action'],value['output'],budget)
 try:project=configuration()
 except TaskDataError:
  if command=='detail':raise
  project=None
 if command=='snapshot':return collect_snapshot(project,budget)
 return collect_detail(project,value['agent_id'],budget,value['output'],value['scope'])

def main():
 started=time.monotonic()
 def cancel(*args):raise SystemExit(143)
 signal.signal(signal.SIGTERM,cancel)
 try:
  raw=sys.stdin.read(8193)
  if len(raw)>8192 or len(sys.argv)!=2:raise ReadError('invalid-request')
  result=request(sys.argv[1],json.loads(raw))
 except (ReadError,TaskDataError) as error:result={'schema':1,'ok':False,'reason_code':error.code}
 except (ValueError,TypeError,KeyError,OSError,RecursionError):result={'schema':1,'ok':False,'reason_code':'invalid-request'}
 result['elapsed_ms']=math.ceil((time.monotonic()-started)*1000)
 print(json.dumps(result,ensure_ascii=False));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
