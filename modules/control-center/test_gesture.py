import unittest
from gesture_model import ThreeFingerSwipe, TouchFrames

class GestureTests(unittest.TestCase):
 def swipe(self,n=3,dx=0,dy=.15):
  g=ThreeFingerSwipe();g.frame({i:(.2+i*.15,.2) for i in range(n)},0)
  g.frame({i:(.2+i*.15+dx,.2+dy) for i in range(n)},.3)
  return g.frame({},.4)
 def test_three_fingers_down_commits_once_on_release(self):
  self.assertTrue(self.swipe())
 def test_two_four_horizontal_up_and_tap_rejected(self):
  for n,dx,dy in [(2,0,.2),(4,0,.2),(3,.3,.02),(3,0,-.2),(3,0,.01)]:
   self.assertFalse(self.swipe(n,dx,dy))
 def test_fourth_contact_cancels_entire_gesture(self):
  g=ThreeFingerSwipe();g.frame({i:(.2,.2) for i in range(3)},0)
  g.frame({i:(.2,.4) for i in range(4)},.3)
  self.assertFalse(g.frame({},.4))
 def test_old_contact_replaced_does_not_become_swipe(self):
  g=ThreeFingerSwipe();g.frame({i:(.2,.2) for i in range(3)},0)
  g.frame({i:(.2,.4) for i in (1,2,3)},.3)
  self.assertFalse(g.frame({},.4))
 def test_slow_hold_is_not_swipe(self):
  g=ThreeFingerSwipe();g.frame({i:(.2,.2) for i in range(3)},0)
  g.frame({i:(.2,.4) for i in range(3)},3)
  self.assertFalse(g.frame({},3.1))
 def test_slot_coordinates_survive_contact_id_changes(self):
  stream=TouchFrames(0,1000,0,1000)
  for cycle in range(2):
   for i in range(3):
    stream.event(3,47,i,cycle)
    stream.event(3,57,i+cycle*10,cycle)
    stream.event(3,53,200+i*100,cycle)
    if cycle==0:stream.event(3,54,200,cycle)
   stream.event(0,0,0,cycle)
   for i in range(3):
    stream.event(3,47,i,cycle+.2);stream.event(3,54,400+cycle*150,cycle+.2)
   stream.event(0,0,0,cycle+.2)
   for i in range(3):stream.event(3,47,i,cycle+.3);stream.event(3,57,-1,cycle+.3)
   self.assertTrue(stream.event(0,0,0,cycle+.3))
 def test_dropped_kernel_frame_never_triggers(self):
  stream=TouchFrames(0,1000,0,1000)
  stream.event(0,3,0,0)
  self.assertFalse(stream.event(0,0,0,.3))
