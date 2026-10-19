"""Exercise real pinned bar sections and official buttons in an isolated runtime."""
import unittest
from layout_probe import measure_layout

CONFIG={'centerAnchor':'clock','layout':{'left':[], 'center':[{'id':'menu','kind':'icon'},{'id':'clock','kind':'text','text':'10月19日 12:00'}], 'right':[{'id':'device','kind':'icon','primary':True}]}}
class BarLayout(unittest.TestCase):
 def test_touch_targets(self):
  result=measure_layout(CONFIG,'touch',(1536,864),1)
  self.assertTrue(result['fits'],result)
  target=next(t for t in result['targets'] if t['id']=='device')
  self.assertGreaterEqual(target['width'],48);self.assertGreaterEqual(target['height'],48)
  self.assertGreaterEqual(result['bar_height'],56)
 def test_compact_has_original_dimensions(self):
  result=measure_layout(CONFIG,'compact',(1536,864),1)
  target=next(t for t in result['targets'] if t['id']=='device')
  self.assertEqual(target['width'],27);self.assertEqual(result['bar_height'],26)
 def test_overflow_rejected(self):
  config={**CONFIG,'layout':{**CONFIG['layout'],'right':[{'id':'device'+str(i),'kind':'icon','primary':True} for i in range(12)]}}
  result=measure_layout(config,'touch',(320,480),1.5)
  self.assertFalse(result['fits']);self.assertEqual(result['reason'],'layout-overflow')
  self.assertEqual(len(result['targets']),14)
 def test_fonts_and_viewports(self):
  for viewport in [(1536,864),(864,1536),(320,480)]:
   for scale in (1,1.25,1.5):
    with self.subTest(viewport=viewport,scale=scale):
     result=measure_layout(CONFIG,'touch',viewport,scale)
     self.assertEqual(len(result['targets']),3)
     self.assertTrue(result['fits'] or result['reason']=='layout-overflow')
     for t in result['targets']:self.assertGreater(t['width'],0)
 def test_long_text_rejected_not_removed(self):
  config={**CONFIG,'layout':{**CONFIG['layout'],'center':[{'id':'clock','kind':'text','text':'非常长的中文状态 '*30}]}}
  result=measure_layout(config,'touch',(864,1536),1.5)
  self.assertFalse(result['fits']);self.assertEqual(len(result['targets']),2)
if __name__=='__main__':unittest.main()
