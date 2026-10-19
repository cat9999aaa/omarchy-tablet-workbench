"""Optional installer-side project config transaction; never called by the panel."""
import hashlib,json,os
from pathlib import Path
from task_model import project_path

def no_links(path):
 path=Path(path).absolute()
 for p in [path,*path.parents]:
  if p.is_symlink():raise ValueError('linked-config-path')
 return path

def prepare(path,project):
 path=no_links(path);project=project_path(project)
 path.parent.mkdir(parents=True,exist_ok=True);no_links(path)
 data=(json.dumps({'schema':1,'project_root':str(project)})+'\n').encode()
 try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 except FileExistsError:
  if not path.is_file() or path.is_symlink():raise ValueError('invalid-config-path')
  return {'created':False}
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return {'created':True,'sha256':hashlib.sha256(data).hexdigest()}

def restore(path,receipt):
 if receipt.get('created') is not True:return True
 try:
  path=no_links(path)
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt.get('sha256'):return False
  path.unlink();return True
 except (OSError,ValueError):return False
