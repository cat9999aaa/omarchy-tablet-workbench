import unittest
import client
from build_ime import EXPECTED_TESTS
class ClientTests(unittest.TestCase):
 def test_shell_option_and_traversal_inputs_rejected(self):
  for args in [('-oProxyCommand=bad','/safe','job'),('host','/a/../b','job'),('host','/safe','../bad'),('host','/x;cmd','job')]:
   with self.assertRaises(ValueError):client.validate(*args)
  self.assertEqual(client.validate('build-host','/home/user/build','ime-01'),'/home/user/build/jobs/ime-01')
 def test_stale_or_incomplete_build_cannot_be_fetched_as_success(self):
  config={'source_files':{'a':'hash'},'target_abi':'abi'}
  good={**config,'job':'job','status':'passed','tests':list(EXPECTED_TESTS)}
  client.check_result(good,'job',config,'abi')
  for bad in [{**good,'job':'other'},{**good,'source_files':{}},{**good,'tests':[]},{**good,'status':'running'}]:
   with self.assertRaises(ValueError):client.check_result(bad,'job',config,'abi')
  with self.assertRaises(ValueError):client.check_result(good,'job',config,'new ABI')
if __name__=='__main__':unittest.main()
