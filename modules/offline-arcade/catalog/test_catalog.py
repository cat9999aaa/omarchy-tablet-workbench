import json
from pathlib import Path
import tempfile
import unittest
from catalog import build, family, safe_label


class CatalogTests(unittest.TestCase):
    def test_parent_cycle_stops(self):
        self.assertIn(family('a', {'a':{'cloneof':'b'}, 'b':{'cloneof':'a'}}), ('a','b'))

    def test_duplicate_files_clones_and_bios_remain_on_disk(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);library=root/'library'
            for d in ['MAME 中文典藏版 v4.00/roms','old/roms']:
                (library/d).mkdir(parents=True)
            for name,d in [('parent','MAME 中文典藏版 v4.00'),('parent','old'),('child','old'),('bios','old')]:
                (library/d/'roms'/(name+'.zip')).write_bytes(b'untouched')
            (library/'mamecn.lst').write_text('parent\t中文游戏 (世界版)\n',encoding='utf-8-sig')
            meta=root/'meta.xml';meta.write_text('<datafile><game name="parent"/><game name="child" cloneof="parent"/><game name="bios" isbios="yes"/></datafile>')
            cats=root/'catver.ini';cats.write_text('[Category]\nparent=Fighter / 2.5D\nchild=Fighter / 2.5D\n')
            lists,report=build(library,meta,cats,root/'cheats')
            self.assertEqual(report['preferred_games'],1)
            self.assertEqual(report['variant_games'],1)
            self.assertEqual(report['duplicate_copies'],1)
            self.assertEqual(report['resources_excluded'],['bios'])
            self.assertEqual(report['pending_chinese'],[])
            self.assertEqual(len(lists['03-动作闯关']),1)
            self.assertEqual(len(list(library.rglob('*.zip'))),4)
            self.assertTrue(all(p.read_bytes()==b'untouched' for p in library.rglob('*.zip')))

    def test_thumbnail_filename_is_safe(self):
        self.assertEqual(safe_label('甲/乙:丙? [game]'),'甲_乙_丙_ [game]')


if __name__=='__main__':unittest.main()
