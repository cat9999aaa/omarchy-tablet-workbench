from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime_host import Host

class RuntimeVerification(unittest.TestCase):
    def test_compact_requires_actual_original_height(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);theme=home/'.local/state/omarchy/current/theme/shell.toml'
            theme.parent.mkdir(parents=True);theme.write_text('[bar]\nsize-horizontal=30\nicon-slot=31\n')
            host=Host(home);host.visible_ids={'pcadmin.control-center'}
            row={'id':'pcadmin.control-center','x':0,'y':0,'width':56,'height':56,'visible':True,'itemVisible':True}
            with patch.object(host,'context',return_value={'viewport':[1536,864]}),patch.object(host,'geometry',return_value=[row]),patch('runtime_host.time.sleep'):
                self.assertFalse(host.verify('compact'))
                row['height']=30
                self.assertTrue(host.verify('compact'))

if __name__=='__main__':unittest.main()
