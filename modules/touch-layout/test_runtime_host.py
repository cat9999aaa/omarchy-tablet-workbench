from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime_host import Host

class RuntimeVerification(unittest.TestCase):
    def test_matching_font_override_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);config=home/'.config/omarchy/shell.toml';config.parent.mkdir(parents=True)
            theme=home/'.local/state/omarchy/current/theme';theme.mkdir(parents=True)
            (theme.parent/'theme.name').write_text('dashen-overdrive')
            (theme/'colors.toml').write_text('foreground="#ffffff"')
            (theme/'shell.toml').write_text('[bar]\nsize-horizontal=26\n')
            config.write_text('[font]\nbase-size=12\n')
            def command(args):
                if args[0]=='hyprctl':return '[{"name":"test","scale":1,"width":1536,"height":864}]'
                if args[-1]=='isLocked':return 'false'
                return '{"bar":{"id":"test.bar","position":"bottom"}}'
            with patch('runtime_host.command',side_effect=command):
                self.assertEqual(Host(home).context()['viewport'],[1536,864])
                self.assertEqual(config.read_text(),'[font]\nbase-size=12\n')
                config.write_text('[font]\nbase-size=15\n')
                with self.assertRaises(ValueError):Host(home).context()
    def test_active_versioned_bar_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);plugin=home/'.config/omarchy/plugins/test.bar'
            (plugin/'release-3').mkdir(parents=True)
            (plugin/'manifest.json').write_text('{"id":"test.bar","entryPoints":{"bar":"release-3/Bar.qml"}}')
            (plugin/'release-3/Bar.qml').write_text('active')
            self.assertEqual(Host(home).bar_source('test.bar'),plugin/'release-3')
            (plugin/'manifest.json').write_text('{"id":"test.bar","entryPoints":{"bar":"../escape.qml"}}')
            with self.assertRaises(ValueError):Host(home).bar_source('test.bar')
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
