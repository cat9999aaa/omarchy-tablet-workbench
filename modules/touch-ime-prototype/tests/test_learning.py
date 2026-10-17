from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='omt-learning-') as tmp:
 p=Path(tmp)
 def run(mode):subprocess.run([str(root/'build/test_learning'),str(root/'rime'),str(p),mode],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 def learned():return any('你好' in f.read_text(errors='replace') for f in p.rglob('*.userdb.txt'))
 run('off');assert not learned(),'private schema must not learn the committed phrase'
 run('on');assert learned(),'enabled learning must persist to user-dictionary snapshot'
 run('off');assert learned(),'pausing learning must preserve existing saved data'
 print('PASS isolated dictionary: paused does not learn; enabled persists; reopening retains data')
