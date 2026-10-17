import unittest
from unittest.mock import patch
import network
class MapLaunch(unittest.TestCase):
 def test_check_before_launch_without_starting_service(self):
  with patch('network.flight_requested',return_value=False),patch('network.call') as check,patch('network.subprocess.Popen') as launch:
   network.action('gps-map')
   args=network.action_command('gps-map')
   check.assert_called_once_with(args+['--check'])
   self.assertEqual(launch.call_args.args[0],args)
 def test_failed_check_does_not_launch(self):
  with patch('network.flight_requested',return_value=False),patch('network.call',side_effect=RuntimeError('adapter not ready')),patch('network.subprocess.Popen') as launch:
   with self.assertRaises(RuntimeError):network.action('gps-map')
   launch.assert_not_called()
 def test_flight_mode_does_not_activate_map_location(self):
  with patch('network.flight_requested',return_value=True),patch('network.call') as call,patch('network.subprocess.Popen') as launch:
   with self.assertRaises(RuntimeError):network.action('gps-map')
   call.assert_not_called();launch.assert_not_called()
