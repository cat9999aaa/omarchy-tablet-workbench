import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('prepare_runtime_tested',Path(__file__).parents[1]/'integration/prepare_runtime.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SelectionTests(unittest.TestCase):
 def test_unique_current_node_required(self):
  node={'id':'n','credential':'fixture-credential','server':'fixture.example','port':443}
  config={'outbounds':[{'tag':'proxy','settings':{'id':'fixture-credential','address':'fixture.example','port':443}}]}
  self.assertEqual(m.select([node],config),node)
  for nodes in ([],[node,node],[dict(node,port=80)]):
   with self.assertRaises(ValueError):m.select(nodes,config)
if __name__=='__main__':unittest.main()
