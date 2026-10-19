#!/usr/bin/python3
"""On-demand, compare-before-write theme dimensions. No services or shell evaluation.

The CLI has fixed home-relative targets. Host injection is a Python test seam,
never an input accepted from the UI. Unfinished transactions block new writes.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import tomllib
import uuid

KEYS = ('size-horizontal', 'icon-slot')

def digest(data): return hashlib.sha256(data.encode()).hexdigest()

def profile_tokens(name):
    if name not in ('touch','compact'): raise ValueError('unknown-profile')
    return dict(zip(KEYS,(56,48))) if name=='touch' else {}

def read(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size>65536: raise ValueError('unsafe-file')
    return path.read_text()

def patch(text, tokens):
    """Patch only plain integer keys in a plain [bar] section; preserve all else.

    tomllib validates semantic structure first. Unsupported textual structures
    are rejected, not rewritten by a general-purpose regular expression.
    """
    parsed=tomllib.loads(text)
    if not isinstance(parsed.get('bar'),dict):raise ValueError('missing-bar')
    for key in KEYS:
        value=parsed['bar'].get(key)
        if key in parsed['bar'] and (type(value) is not int or not 16<=value<=128):raise ValueError('invalid-size')
    lines=text.splitlines(keepends=True);start=None;end=len(lines);found={}
    for i,line in enumerate(lines):
        stripped=line.strip()
        if stripped.startswith('['):
            if start is not None:end=i;break
            if stripped=='[bar]':start=i+1
    if start is None:raise ValueError('unsupported-bar-syntax')
    for i in range(start,end):
        line=lines[i]
        if not line.strip() or line.lstrip().startswith('#'):continue
        match=re.fullmatch(r'([ \t]*)([a-z][a-z0-9-]*)([ \t]*=[ \t]*)([^\n]*)(\n?)',line)
        if not match:raise ValueError('unsupported-bar-syntax')
        key=match[2]
        if key in KEYS:
            value=re.fullmatch(r'([0-9]+)([ \t]*(?:#[^\n]*)?)',match[4])
            if not value:raise ValueError('unsupported-size-syntax')
            found[key]=i
            if key in tokens:lines[i]=match[1]+key+match[3]+str(tokens[key])+value[2]+match[5]
    if set(found)!=set(KEYS)&set(parsed['bar']):raise ValueError('ambiguous-size-syntax')
    missing=[key for key in tokens if key not in found]
    if missing:
        if end and not lines[end-1].endswith('\n'):lines[end-1]+='\n'
        lines[end:end]=[key+' = '+str(tokens[key])+'\n' for key in missing]
    result=''.join(lines);tomllib.loads(result)
    return result

def atomic(path, text):
    fd,name=tempfile.mkstemp(prefix='.touch-layout-',dir=path.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

class Manager:
    def __init__(self, root, host=None):
        self.root=Path(root)
        self.targets=(self.root/'.config/omarchy/themes/dashen-overdrive/shell.toml',self.root/'.local/state/omarchy/current/theme/shell.toml')
        self.state_dir=self.root/'.local/state/dashen-overdrive/touch-layout'
        self.state_path=self.state_dir/'state.json'
        if host is None:
            from runtime_host import Host
            host=Host(self.root)
        self.host=host
    def result(self, profile='unknown',health='unverified',reason='',**extra):
        return dict(schema_version=1,profile=profile,health=health,reason=reason,**extra)
    def state(self):
        return json.loads(read(self.state_path)) if self.state_path.exists() else None
    def contents(self):
        for path in self.targets:
            if path.resolve()!=path:raise ValueError('symlink-target')
        return [read(path) for path in self.targets]
    def status(self):
        try:
            state=self.state()
            if not state:return self.result('compact','ready','original-dimensions')
            if state['phase']!='committed':return self.result(state['profile'],'unverified','unfinished-transaction')
            if self.contents()!=state['after']:return self.result(state['profile'],'conflict','theme-changed')
            return self.result(state['profile'],'ready','',transaction_id=state['id'])
        except (OSError,ValueError,KeyError):return self.result(reason='invalid-state')
    def plan(self, profile):
        try:
            tokens=profile_tokens(profile);context=self.host.context()
            if context.get('theme')!='dashen-overdrive' or context.get('position')!='bottom' or not context.get('output'):raise ValueError('unsupported-context')
            before=self.contents();state=self.state()
            if state and (state['phase']!='committed' or state['after']!=before):return self.result(profile,'conflict','theme-changed-or-unfinished')
            for text in before:patch(text,{})
            baseline=state['baseline'] if state else before
            after=[patch(text,tokens) for text in before] if profile=='touch' else baseline
            measured=self.host.measure(profile, after[1])
            if measured.get('fits') is not True:raise ValueError(measured.get('reason','layout-unverified'))
            identity={'profile':profile,'context':context,'before':before,'after':after,'state_id':state['id'] if state else None}
            plan_id=profile+':'+digest(json.dumps(identity,sort_keys=True))
            return self.result(profile,'ready','',plan_id=plan_id,context=context,before=before,after=after,baseline=baseline)
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError) as error:return self.result(profile,reason=str(error))
    @contextlib.contextmanager
    def locked(self):
        self.state_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.state_dir.resolve()!=self.state_dir:raise ValueError('symlink-state')
        fd=os.open(self.state_dir/'lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);yield
        finally:os.close(fd)
    def save(self,path,value):atomic(path,json.dumps(value,ensure_ascii=False,sort_keys=True)+'\n')
    def previous(self,tx):
        identity=tx.get('previous_id')
        if identity is None:return None
        if not isinstance(identity,str) or not re.fullmatch('[0-9a-f]{32}',identity):raise ValueError('invalid-history')
        return json.loads(read(self.state_dir/(identity+'.json')))
    def reload(self):
        try:return self.host.reload()
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):return False
    def restore(self,tx):
        conflicts=[]
        for i,path in reversed(list(enumerate(self.targets))):
            try:current=read(path)
            except (OSError,ValueError):conflicts.append(i);continue
            if current==tx['before'][i]:continue
            if current!=tx['after'][i]:conflicts.append(i);continue
            atomic(path,tx['before'][i])
        return not conflicts
    def apply(self, plan_id):
        if not isinstance(plan_id,str) or not re.fullmatch(r'(touch|compact):[0-9a-f]{64}',plan_id):return self.result(reason='invalid-plan')
        profile=plan_id.split(':')[0]
        try:
            with self.locked():
                planned=self.plan(profile)
                if planned.get('plan_id')!=plan_id:return self.result(profile,'conflict','plan-changed')
                previous=self.state()
                if previous and previous['profile']==profile:
                    if not self.host.verify(profile):return self.result(profile,'unverified','actual-state-mismatch',transaction_id=previous['id'])
                    return self.result(profile,'applied','already-applied',transaction_id=previous['id'])
                tx={**planned,'id':uuid.uuid4().hex,'phase':'prepared','previous_id':previous['id'] if previous else None}
                self.save(self.state_dir/(tx['id']+'.json'),tx);self.save(self.state_path,tx)
                try:
                    for i,path in enumerate(self.targets):
                        if read(path)!=tx['before'][i] or self.host.context()!=tx['context']:raise ValueError('concurrent-change')
                        atomic(path,tx['after'][i])
                    if not self.reload() or not self.host.verify(profile):raise ValueError('reload-or-geometry-failed')
                    if self.contents()!=tx['after'] or self.host.context()!=tx['context']:raise ValueError('concurrent-change')
                except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
                    restored=self.restore(tx)
                    reloaded=self.reload() if restored else False
                    tx['phase']='rolled-back' if restored else 'conflict';self.save(self.state_dir/(tx['id']+'.json'),tx)
                    if restored:
                        if previous:self.save(self.state_path,previous)
                        else:self.state_path.unlink()
                    else:self.save(self.state_path,tx)
                    return self.result(profile,'unverified' if restored else 'conflict',str(error),restored=restored,reload_verified=reloaded)
                tx['phase']='committed';self.save(self.state_dir/(tx['id']+'.json'),tx);self.save(self.state_path,tx)
                return self.result(profile,'applied','',transaction_id=tx['id'])
        except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:return self.result(profile,reason=str(error))
    def rollback(self, transaction_id):
        if not isinstance(transaction_id,str) or not re.fullmatch('[0-9a-f]{32}',transaction_id):return self.result(reason='invalid-transaction')
        try:
            with self.locked():
                tx=self.state()
                if not tx or tx['id']!=transaction_id:return self.result(health='conflict',reason='transaction-not-current')
                if not self.restore(tx):return self.result(tx['profile'],'conflict','theme-changed')
                if not self.reload():return self.result(tx['profile'],reason='reload-failed')
                if self.contents()!=tx['before']:return self.result(tx['profile'],'conflict','theme-changed')
                previous=self.previous(tx)
                if previous:self.save(self.state_path,previous)
                else:self.state_path.unlink()
                tx['phase']='rolled-back';self.save(self.state_dir/(tx['id']+'.json'),tx)
                return self.result(previous['profile'] if previous else 'compact','rolled-back','')
        except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:return self.result(reason=str(error))

def plan(root,profile,evidence=None):
    # Caller-provided evidence cannot authorize a write; collect with fixed Host.
    return Manager(root).plan(profile)
def apply(root,plan_id):return Manager(root).apply(plan_id)
def rollback(root,transaction_id):return Manager(root).rollback(transaction_id)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['status','plan','apply','rollback']);parser.add_argument('value',nargs='?')
    args=parser.parse_args();manager=Manager(Path.home())
    result=manager.status() if args.action=='status' else getattr(manager,args.action)(args.value)
    # Do not expose backup contents or context through the UI protocol.
    public={k:v for k,v in result.items() if k in {'schema_version','profile','health','reason','plan_id','transaction_id','restored','reload_verified'}}
    print(json.dumps(public,ensure_ascii=False));return 0 if public['health'] in ('ready','applied','rolled-back') else 1
if __name__=='__main__':raise SystemExit(main())
