import unittest
from unittest.mock import patch
import navigation as n

class TouchActions(unittest.TestCase):
    def test_fixed_profile_actions(self):
        for name,profile in [('layout-touch','touch'),('layout-compact','compact')]:
            with patch.object(n,'unlocked',return_value=True),patch.object(n,'read_json',side_effect=[[{'name':'HEADLESS-2','focused':True}],{},False]),patch.object(n,'layout_action',return_value={'ok':True}) as action:
                self.assertTrue(n.action({'action':name,'context':{'output':'HEADLESS-2'},'target':None})['ok'])
                action.assert_called_once_with(profile,'HEADLESS-2')
    def test_locked_or_changed_context_never_applies(self):
        with patch.object(n,'unlocked',return_value=False),patch.object(n,'layout_action') as action:
            self.assertFalse(n.action({'action':'layout-touch','context':{'output':'HEADLESS-2'}})['ok']);action.assert_not_called()
        with patch.object(n,'unlocked',return_value=True),patch.object(n,'read_json',side_effect=n.ReadError('context-changed')),patch.object(n,'layout_action') as action:
            self.assertFalse(n.action({'action':'layout-touch','context':{'output':'HEADLESS-2'}})['ok']);action.assert_not_called()
    def test_unknown_profile_rejected(self):
        with patch.object(n,'unlocked',return_value=True),patch.object(n,'read_json',side_effect=[[{'name':'HEADLESS-2','focused':True}],{},False]),patch.object(n,'layout_action') as action:
            with self.assertRaises(ValueError):n.action({'action':'layout-other','context':{'output':'HEADLESS-2'},'target':None})
            action.assert_not_called()
if __name__=='__main__':unittest.main()
