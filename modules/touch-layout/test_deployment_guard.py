import hashlib
import unittest
from deployment_guard import verify_plugins_restored
class RecoveryGuardTests(unittest.TestCase):
    def test_failed_unrecorded_apply_blocks_helper_restore(self):
        originals={'control':{'sha256':hashlib.sha256(b'old-control').hexdigest(),'version':'old'},'navigation':{'sha256':hashlib.sha256(b'old-navigation').hexdigest(),'version':'old'}}
        manifests={'control':b'old-control','navigation':b'new-navigation'}
        versions={'control':'old','navigation':'new'}
        self.assertFalse(verify_plugins_restored(originals,manifests.__getitem__,versions.__getitem__))
        manifests['navigation']=b'old-navigation'
        self.assertFalse(verify_plugins_restored(originals,manifests.__getitem__,versions.__getitem__))
        versions['navigation']='old'
        self.assertTrue(verify_plugins_restored(originals,manifests.__getitem__,versions.__getitem__))
    def test_missing_runtime_proof_blocks_restore(self):
        def missing(key):raise RuntimeError('unavailable')
        self.assertFalse(verify_plugins_restored({'navigation':{'sha256':'x','version':'old'}},missing,missing))
if __name__=='__main__':unittest.main()
