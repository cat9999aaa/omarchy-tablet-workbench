import unittest
from metrics import Metrics
class MetricsTests(unittest.TestCase):
 def test_touch_does_not_invent_pressure(self):
  m=Metrics();m.add('touch',True,{'pressure':None});self.assertIsNone(m.summary()['axes']['pressure']);self.assertEqual(m.contacts,1)
 def test_actual_axes_range(self):
  m=Metrics();m.add('pen',True,{'pressure':0.2,'xtilt':-0.4});m.add('pen',False,{'pressure':0.8,'xtilt':0.1});self.assertEqual(m.summary()['axes']['pressure'],[0.2,0.8]);self.assertEqual(m.contacts,1)
 def test_summary_excludes_ink(self):
  m=Metrics();m.add('touch',False,{});self.assertNotIn('points',m.summary());self.assertEqual(m.events,1)
if __name__=='__main__':unittest.main()
