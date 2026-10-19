"""Strict, pure projection of Paseo CLI metadata. Never retain source text."""
from datetime import datetime,timezone
from pathlib import Path
import re

STATUSES=frozenset(('initializing','idle','running','error','closed'))
class TaskDataError(ValueError):
 def __init__(self,code='invalid-data'):self.code=code;super().__init__(code)
def agent_id(value):
 if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):raise TaskDataError()
 return value.lower()
def state_kind(status,pending):
 if pending is not None and (type(pending) is not int or pending<0):return 'unknown'
 if pending:return 'needs_permission'
 return status if isinstance(status,str) and status in STATUSES else 'unknown'
def project_path(project):
 try:
  p=Path(project)
  if not p.is_absolute():raise TaskDataError('invalid-project')
  p=p.resolve(strict=True)
  if not p.is_dir():raise TaskDataError('invalid-project')
  return p
 except (OSError,RuntimeError,ValueError):raise TaskDataError('invalid-project') from None
def in_project(value,project,home):
 if not isinstance(value,str) or not value or len(value)>4096 or any(ord(c)<32 for c in value):raise TaskDataError()
 if value=='~':value=str(home)
 elif value.startswith('~/'):value=str(Path(home)/value[2:])
 p=Path(value)
 if not p.is_absolute():raise TaskDataError()
 try:p=p.resolve(strict=True)
 except (OSError,RuntimeError):return False
 return p.is_dir() and (p==project or project in p.parents)
def project_rows(raw,project,home):
 project=project_path(project)
 if not isinstance(raw,list):raise TaskDataError()
 seen={}
 for item in raw:
  if not isinstance(item,dict):raise TaskDataError()
  if not in_project(item.get('cwd'),project,home):continue
  key=agent_id(item.get('id'));row={'agent_id':key,'status':state_kind(item.get('status'),None)}
  if key in seen and seen[key]!=row:raise TaskDataError()
  seen[key]=row
 return [seen[k] for k in sorted(seen)]
def source_time(value):
 if not isinstance(value,str) or len(value)>64:return None
 try:
  t=datetime.fromisoformat(value.replace('Z','+00:00'))
  if t.tzinfo is None or t>datetime.now(timezone.utc):return None
  return value
 except (ValueError,OverflowError):return None
def project_detail(raw,requested,project,home):
 project=project_path(project)
 if not isinstance(raw,dict) or agent_id(raw.get('Id'))!=agent_id(requested) or not in_project(raw.get('Cwd'),project,home):raise TaskDataError('scope-changed')
 pending=raw.get('PendingPermissions')
 if pending is not None and (not isinstance(pending,list) or any(not isinstance(p,dict) for p in pending)):raise TaskDataError()
 return {'status':state_kind(raw.get('Status'),None),'pending_permission_count':len(pending) if pending is not None else None,'source_updated_at':source_time(raw.get('UpdatedAt'))}
