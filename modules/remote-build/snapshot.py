"""Allowlisted source snapshots and strict artifact/archive verification."""
import hashlib,tarfile
from pathlib import Path,PurePosixPath
TOP={'CMakeLists.txt','omtbridge.conf.in','manifest.json','README.md','control.py'}
RIME={'omt_t9.schema.yaml','omt_full.schema.yaml','default.custom.yaml','omt_t9_private.schema.yaml','omt_full_private.schema.yaml'}
DIRS={'src','qml','tests','rime','vendor'}
SUFFIXES={'.cpp','.h','.qml','.js','.py','.json','.yaml','.md','.txt','.model'}
def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def source_files(source):
 source=Path(source).resolve()
 for p in sorted(source.rglob('*')):
  r=p.relative_to(source)
  if r.parts[0] not in TOP|DIRS:continue
  if r.parts[0]=='rime' and (len(r.parts)!=2 or r.name not in RIME):continue
  if any(x in ('build','__pycache__','.git') or '.userdb' in x for x in r.parts):continue
  if p.is_symlink():raise ValueError('Source links are not allowed: '+str(r))
  if p.is_file() and (str(r) in TOP or p.suffix in SUFFIXES or 'LICENSE' in p.name):yield p,r.as_posix()
def create_snapshot(source,archive):
 files=list(source_files(source));manifest={r:digest(p) for p,r in files}
 if 'CMakeLists.txt' not in manifest:raise ValueError('Not an IME source tree')
 with tarfile.open(archive,'w:gz') as t:
  for p,r in files:t.add(p,arcname=r,recursive=False)
 return manifest
def verify_archive(archive,manifest):
 seen=set()
 with tarfile.open(archive,'r:*') as t:
  for m in t:
   p=PurePosixPath(m.name)
   if p.is_absolute() or '..' in p.parts or not m.isfile() or m.name in seen:raise ValueError('Unsafe archive member')
   if m.name not in manifest:raise ValueError('Unexpected archive member')
   with t.extractfile(m) as f:got=hashlib.file_digest(f,'sha256').hexdigest()
   if got!=manifest[m.name]:raise ValueError('Archive checksum mismatch: '+m.name)
   seen.add(m.name)
 if seen!=set(manifest):raise ValueError('Archive files missing')
 return True
