"""Bounded read-only navigation input. No persistent processes or raw error logs."""
import json
import math
import os
import re
import selectors
import signal
import subprocess
import time

class ReadError(Exception):
 def __init__(self,code):
  self.code=code
  super().__init__(code)

class ReadBudget:
 def __init__(self,total_seconds=5.0,clock=time.monotonic,max_read_seconds=1.0):
  if not math.isfinite(total_seconds) or total_seconds<=0:raise ValueError('invalid budget')
  if not math.isfinite(max_read_seconds) or max_read_seconds<=0:raise ValueError('invalid read cap')
  self.max_read_seconds=max_read_seconds
  self.clock=clock;self.deadline=clock()+total_seconds
 def timeout(self):
  remaining=self.deadline-self.clock()
  if remaining<=0:raise ReadError('timeout')
  return min(self.max_read_seconds,remaining)

def _read(argv,budget,max_bytes=1048576,text_only=False):
 duration=budget.timeout()
 deadline=budget.clock()+duration
 proc=None;completed=False
 try:
  proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
  chunks=[];size=0
  with selectors.DefaultSelector() as sel:
   sel.register(proc.stdout,selectors.EVENT_READ)
   while True:
    remaining=min(deadline,budget.deadline)-budget.clock()
    if remaining<=0:raise ReadError('timeout')
    if not sel.select(remaining):raise ReadError('timeout')
    chunk=os.read(proc.stdout.fileno(),min(65536,max_bytes-size+1))
    if not chunk:break
    size+=len(chunk)
    if size>max_bytes:raise ReadError('invalid-data')
    chunks.append(chunk)
  remaining=min(deadline,budget.deadline)-budget.clock()
  if remaining<=0:raise ReadError('timeout')
  if proc.wait(timeout=remaining)!=0:raise ReadError('read-failed')
  if text_only:
   try:result=b''.join(chunks).decode('utf-8')
   except UnicodeError:raise ReadError('invalid-data') from None
   completed=True
   return result
  def invalid_constant(value):raise ValueError('non-finite')
  try:result=json.loads(b''.join(chunks).decode('utf-8'),parse_constant=invalid_constant)
  except (UnicodeError,ValueError,RecursionError):raise ReadError('invalid-data') from None
  completed=True
  return result
 except subprocess.TimeoutExpired:raise ReadError('timeout') from None
 except OSError:raise ReadError('read-failed') from None
 finally:
  if proc is not None:
   if not completed:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
   proc.wait()
   proc.stdout.close()

def check_lock(value):
 if value is True:raise ReadError('locked')
 if value is not False:raise ReadError('lock-unknown')

def focused_output(value):
 if not isinstance(value,list):raise ReadError('invalid-data')
 focused=[];names=set()
 for m in value:
  if not isinstance(m,dict):raise ReadError('invalid-data')
  name=m.get('name')
  if not isinstance(name,str) or not name.strip() or len(name)>256 or any(ord(c)<32 or ord(c)==127 for c in name):raise ReadError('invalid-data')
  if name in names or type(m.get('focused')) is not bool or type(m.get('disabled',False)) is not bool:raise ReadError('invalid-data')
  names.add(name)
  if m['focused'] and not m.get('disabled',False):focused.append(name)
 if len(focused)!=1:raise ReadError('output-unavailable')
 return focused[0]

def window_identity(value):
 if not isinstance(value,dict):raise ReadError('invalid-data')
 if not value:return None
 address=value.get('address');pid=value.get('pid')
 if not isinstance(address,str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,16}',address) or int(address,16)==0 or type(pid) is not int or pid<=0:raise ReadError('invalid-data')
 if not isinstance(value.get('class',''),str):raise ReadError('invalid-data')
 return {'address':address,'pid':pid}

def workspace(value):
 if not isinstance(value,dict) or type(value.get('id')) is not int:raise ReadError('invalid-data')
 return value['id']

def workspace_counts(value):
 if not isinstance(value,list):raise ReadError('invalid-data')
 counts={i:0 for i in range(1,11)}
 for client in value:
  if not isinstance(client,dict):raise ReadError('invalid-data')
  number=workspace(client.get('workspace'))
  if number in counts:counts[number]+=1
 return counts

def read_json(argv,budget,max_bytes=1048576):return _read(argv,budget,max_bytes)
def read_text(argv,budget,max_bytes=1048576):return _read(argv,budget,max_bytes,True)


def run_command(argv,budget):
 """Bounded handoff completion; launched apps must not retain a reader pipe."""
 proc=None;completed=False
 try:
  duration=budget.timeout()
  proc=subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
  if proc.wait(timeout=duration)!=0:raise ReadError('read-failed')
  completed=True
 except subprocess.TimeoutExpired:raise ReadError('timeout') from None
 except OSError:raise ReadError('read-failed') from None
 finally:
  if proc is not None:
   if not completed:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
   proc.wait()
