"""Cancellation must reap the snapshot's current external read, not only Python."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

class SnapshotCancellation(unittest.TestCase):
 def test_sigterm_reaps_inflight_read(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);marker=root/'child'
   for name,body in [('omarchy-shell','print("false")'),('hyprctl',f'from pathlib import Path\nimport os,time\nPath({str(marker)!r}).write_text(str(os.getpid()))\ntime.sleep(20)')]:
    path=root/name;path.write_text('#!'+sys.executable+'\n'+body+'\n');path.chmod(0o755)
   proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('navigation.py')),'snapshot'],env={**os.environ,'PATH':str(root)+':'+os.environ['PATH']},stdout=subprocess.PIPE)
   pid=None
   try:
    end=time.monotonic()+2
    while not marker.exists() and time.monotonic()<end:time.sleep(.01)
    self.assertTrue(marker.exists(),'external read never started')
    pid=int(marker.read_text());proc.terminate();proc.communicate(timeout=2)
    end=time.monotonic()+.4
    while Path('/proc',str(pid)).exists() and time.monotonic()<end:time.sleep(.01)
    self.assertFalse(Path('/proc',str(pid)).exists(),'cancelled snapshot left its external reader alive')
   finally:
    if proc.poll() is None:proc.kill();proc.communicate()
    if pid:
     try:os.killpg(pid,signal.SIGKILL)
     except ProcessLookupError:pass
if __name__=='__main__':unittest.main()
