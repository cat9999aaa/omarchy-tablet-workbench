"""Theme validation must reject active content and unreadable palettes."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = HERE / 'check_theme.py'
        if not path.exists():
            raise AssertionError('theme validator interface is missing')
        spec = importlib.util.spec_from_file_location('check_theme', path)
        cls.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.api)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'theme'
        shutil.copytree(ROOT / 'themes/dashen-overdrive', self.path)

    def test_original_theme_and_cli(self):
        self.assertEqual(self.api.validate_theme(self.path), [])
        result = subprocess.run([sys.executable, str(HERE/'check_theme.py'), str(self.path)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_reject_executable_symlink_and_unknown_file(self):
        for name in ['init.lua', 'hook.sh', 'extra.txt']:
            with self.subTest(name=name):
                p = self.path/name; p.write_text('do not run')
                self.assertTrue(self.api.validate_theme(self.path));p.unlink()
        p = self.path/'README.md';p.chmod(0o755)
        self.assertTrue(self.api.validate_theme(self.path));p.chmod(0o644)
        p.unlink();p.symlink_to(self.path/'LICENSE')
        self.assertTrue(self.api.validate_theme(self.path))

    def test_required_palette_and_shell_sections(self):
        for name, text in [('colors.toml','background = "#000000"'),
                           ('colors.toml','background = "#000000"\nbackground = "#ffffff"'),
                           ('shell.toml','[bar]\ntext = "#ffffff"\nunknown = 1'),
                           ('shell.toml','[font]\nbase-size = 8')]:
            p=self.path/name;original=p.read_text()
            with self.subTest(name=name,text=text):
                p.write_text(text);self.assertTrue(self.api.validate_theme(self.path))
            p.write_text(original)
        p=self.path/'colors.toml';p.write_text(p.read_text().replace('#0C1014', 'not-a-color'))
        self.assertTrue(self.api.validate_theme(self.path))

    def test_missing_directory_and_oversized_content(self):
        self.assertTrue(self.api.validate_theme(self.path/'missing'))
        p=self.path/'colors.toml';p.write_text('#' * 16385)
        self.assertTrue(self.api.validate_theme(self.path))
        p=self.path/'README.md';p.write_text('x' * 131073)
        self.assertTrue(self.api.validate_theme(self.path))

    def test_contrast_known_values_and_bad_colors(self):
        self.assertAlmostEqual(self.api.contrast_ratio('#000000','#FFFFFF'),21)
        self.assertEqual(self.api.contrast_ratio('#123456','#123456'),1)
        self.assertGreaterEqual(self.api.contrast_ratio('#E7E9DF','#0C1014'),4.5)
        self.assertGreaterEqual(self.api.contrast_ratio('#FFB454','#0C1014'),3)
        for v in ['red','#fff','#12345678',None]:
            with self.subTest(value=v),self.assertRaises(ValueError):
                self.api.contrast_ratio(v,'#000000')

    def test_low_contrast_rejected_without_mutation(self):
        p=self.path/'colors.toml';p.write_text(p.read_text().replace('#E7E9DF','#0C1014'))
        before=p.read_bytes();self.assertTrue(self.api.validate_theme(self.path));self.assertEqual(p.read_bytes(),before)

    def test_nonfinite_alpha_and_untrusted_alias_rejected(self):
        p=self.path/'shell.toml';original=p.read_text()
        for extra in ['background-alpha = nan', 'background-alpha = 2', 'text = "https://invalid.example"']:
            p.write_text('[bar]\n'+extra)
            self.assertTrue(self.api.validate_theme(self.path))
        p.write_text(original)

if __name__ == '__main__':
    unittest.main()
