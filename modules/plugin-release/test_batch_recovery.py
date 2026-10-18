"""Rehearse the C1 delivery procedure with real per-plugin transactions.

Only official commands/theme effects are injected. This is not a batch publisher
or proof that the production theme hook is safe; that requires its own preflight.
"""
# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from release import ReleaseError, ReleaseManager, pack, sha


class BatchRecovery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        home = patch('release.Path.home', return_value=self.root / 'home')
        home.start()
        self.addCleanup(home.stop)
        self.plugins = self.root / 'plugins'
        self.order = [('pcadmin.control-center', 'control'),
                      ('pcadmin.navigation', 'navigation'),
                      ('pcadmin.network', 'network'), ('pcadmin.power', 'battery')]
        self.before = {}
        self.bundles = {}
        for plugin, _ in self.order:
            path = self.plugins / plugin
            path.mkdir(parents=True)
            old = dict(schemaVersion=1, id=plugin, name=plugin, version='1.0',
                       kinds=['overlay'], entryPoints={'overlay': 'Main.qml'})
            (path / 'manifest.json').write_text(json.dumps(old))
            (path / 'Main.qml').write_text('old UI')
            self.before[plugin] = (path / 'manifest.json').read_bytes()
            payload = self.root / ('payload-' + plugin)
            payload.mkdir()
            (payload / 'Main.qml').write_text('candidate UI')
            source = self.root / (plugin + '.json')
            source.write_text(json.dumps({**old, 'version': '2.0'}))
            target = self.root / ('bundle-' + plugin)
            pack(source, payload, target)
            self.bundles[plugin] = target
        self.preferences = self.root / 'shell.toml'
        self.preferences.write_text('[font]\nbase-size=20\n')
        self.background = self.root / 'background'
        self.background.write_bytes(b'user-background')
        self.theme = self.root / 'theme.name'
        self.theme.write_text('original')
        self.validated = []
        self.restored = []
        self.failure = ''
        self.manager = ReleaseManager(self.plugins, self.root / 'state', self.command, timeout=.02)

    def command(self, args):
        if args == ['omarchy-shell', 'lock', 'isLocked']:
            return 'false'
        if args == ['omarchy-shell', 'pcadmin.controlCenter', 'ready']:
            return 'true'
        if args[:3] == ['omarchy', 'plugin', 'validate']:
            plugin = json.loads((Path(args[3]) / 'manifest.json').read_text())['id']
            self.validated.append(plugin)
            if plugin == self.order[2][0] and self.failure in ('third', 'manifest-conflict'):
                if self.failure == 'manifest-conflict':
                    target = self.plugins / self.order[0][0] / 'manifest.json'
                    target.write_text(json.dumps({**json.loads(target.read_text()), 'description': 'user edit'}))
                raise ReleaseError('injected third-plugin validation failure')
            return ''
        if args == ['omarchy-shell', 'shell', 'rescanPlugins']:
            return ''
        probes = {'pcadmin.controlCenter': ('pcadmin.control-center', True),
                  'pcadmin.navigation': ('pcadmin.navigation', True),
                  'omarchy.network': ('pcadmin.network', False),
                  'omarchy.power': ('pcadmin.power', True)}
        if len(args) == 3 and args[0] == 'omarchy-shell' and args[1] in probes:
            plugin, encoded = probes[args[1]]
            version = json.loads((self.plugins / plugin / 'manifest.json').read_text())['version']
            return json.dumps({'version': version}) if encoded else version
        raise AssertionError(args)

    def rehearse(self, failure):
        self.failure = failure
        applied = []
        conflicts = []
        original_theme = self.theme.read_bytes()
        theme_written = None
        try:
            for plugin, profile in self.order:
                receipt = self.manager.apply(self.bundles[plugin], plugin, profile)
                applied.append((plugin, profile, receipt['transaction']))
            # Inject the external theme command AFTER every plugin has passed.
            self.theme.write_text('dashen-overdrive')
            theme_written = sha(self.theme.read_bytes())
            if failure == 'theme-conflict':
                self.theme.write_text('user-selected-theme')
            raise ReleaseError('injected theme command failure after change')
        except ReleaseError:
            if theme_written is not None:
                if sha(self.theme.read_bytes()) == theme_written:
                    self.theme.write_bytes(original_theme)
                else:
                    conflicts.append('theme')
            for plugin, profile, token in reversed(applied):
                try:
                    self.manager.rollback(plugin, token, profile)
                    self.restored.append(plugin)
                except ReleaseError:
                    conflicts.append(plugin)
        self.assertEqual(self.preferences.read_text(), '[font]\nbase-size=20\n')
        self.assertEqual(self.background.read_bytes(), b'user-background')
        return conflicts

    def assert_original(self, except_plugin=None):
        for plugin, _ in self.order:
            if plugin != except_plugin:
                self.assertEqual((self.plugins / plugin / 'manifest.json').read_bytes(), self.before[plugin])
            self.assertEqual((self.plugins / plugin / 'Main.qml').read_text(), 'old UI')

    def test_third_failure_stops_fourth_and_restores_only_completed_in_reverse(self):
        self.assertEqual(self.rehearse('third'), [])
        self.assertEqual(self.validated, [p for p, _ in self.order[:3]])
        self.assertEqual(self.restored, [p for p, _ in reversed(self.order[:2])])
        self.assert_original()
        self.assertEqual(self.theme.read_text(), 'original')

    def test_theme_failure_restores_theme_then_all_plugins(self):
        self.assertEqual(self.rehearse('theme'), [])
        self.assertEqual(self.validated, [p for p, _ in self.order])
        self.assertEqual(self.restored, [p for p, _ in reversed(self.order)])
        self.assert_original()
        self.assertEqual(self.theme.read_text(), 'original')

    def test_manifest_user_edit_is_preserved_while_other_plugin_is_restored(self):
        plugin = self.order[0][0]
        self.assertEqual(self.rehearse('manifest-conflict'), [plugin])
        self.assertEqual(self.restored, [self.order[1][0]])
        self.assert_original(except_plugin=plugin)
        self.assertEqual(json.loads((self.plugins / plugin / 'manifest.json').read_text())['description'], 'user edit')
        journals = list((self.root / 'state' / plugin).glob('*/transaction.json'))
        self.assertEqual(len(journals), 1)
        self.assertEqual(json.loads(journals[0].read_text())['status'], 'conflict-preserved')

    def test_theme_user_edit_is_preserved_while_all_plugins_are_restored(self):
        self.assertEqual(self.rehearse('theme-conflict'), ['theme'])
        self.assert_original()
        self.assertEqual(self.theme.read_text(), 'user-selected-theme')


if __name__ == '__main__':
    unittest.main()
