"""On-demand local CLI metadata, projected before leaving this process."""
from datetime import datetime,timezone
from pathlib import Path
import time,hashlib,json
from navigation_read import ReadBudget,ReadError,read_json,read_text,run_command,check_lock,focused_output
from task_model import TaskDataError,project_rows,project_detail,agent_id,project_path

def context(budget,expected=None):
 check_lock(read_json(['omarchy-shell','lock','isLocked'],budget))
 output=focused_output(read_json(['hyprctl','monitors','-j'],budget))
 if expected is not None and output!=expected:raise ReadError('context-changed')
 return output

def finish(budget,output):
 context(budget,output);check_lock(read_json(['omarchy-shell','lock','isLocked'],budget));budget.timeout()
 return {'schema':1,'ok':True,'reason_code':'','output':output,'observed_at':datetime.now(timezone.utc).isoformat(),'sampled_boottime_ms':int(time.clock_gettime(time.CLOCK_BOOTTIME)*1000)}

def project_identity(project):
 try:
  path=project_path(project);st=path.stat()
  return (str(path),st.st_dev,st.st_ino)
 except (OSError,TypeError,ValueError):raise TaskDataError('invalid-project')

def scope_token(project):
 return hashlib.sha256(json.dumps(project_identity(project)).encode()).hexdigest()

def source_budget(budget):
 remaining=budget.deadline-budget.clock()-1.25
 if remaining<=0:raise ReadError('timeout')
 return ReadBudget(remaining,clock=budget.clock,max_read_seconds=budget.max_read_seconds)

def collect_snapshot(project,budget):
 output=context(budget);rows=None;reason='';dnd=None;dnd_reason='';scope=None
 try:
  if project is None:raise TaskDataError('invalid-project')
  identity=project_identity(project);scope=scope_token(project)
  reads=source_budget(budget)
  raw=read_json(['paseo','ls','--global','--json'],reads)
  if project_identity(project)!=identity:raise TaskDataError('invalid-project')
  rows=project_rows(raw,project,Path.home())
 except (ReadError,TaskDataError) as error:reason=error.code
 try:
  value=read_text(['omarchy-shell','notifications','isDnd'],source_budget(budget)).strip()
  if value not in ('on','off'):raise ReadError('invalid-data')
  dnd=value=='on'
 except ReadError as error:dnd_reason=error.code
 result=finish(budget,output);result.update(scope=scope,rows=rows,source_reason=reason,dnd=dnd,dnd_reason=dnd_reason);return result

def collect_detail(project,key,budget,expected_output=None,expected_scope=None):
 key=agent_id(key);output=context(budget,expected_output)
 identity=project_identity(project)
 if expected_scope is not None and scope_token(project)!=expected_scope:raise TaskDataError('scope-changed')
 try:
  raw=read_json(['paseo','inspect',key,'--json'],source_budget(budget))
  if project_identity(project)!=identity:raise TaskDataError('invalid-project')
  detail=project_detail(raw,key,project,Path.home())
 except (ReadError,TaskDataError) as error:
  result=finish(budget,output);result.update(ok=False,reason_code=error.code);return result
 result=finish(budget,output);result.update(agent_id=key,detail=detail);return result

def handoff(action,output,budget):
 commands={'open-paseo':['gtk-launch','Paseo'],'notification-history':['omarchy-shell','notifications','showHistory']}
 if action not in commands:raise ReadError('invalid-action')
 context(budget,output);check_lock(read_json(['omarchy-shell','lock','isLocked'],budget))
 run_command(commands[action],budget)
 return {'schema':1,'ok':True,'reason_code':''}
