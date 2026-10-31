"""Offline USB boot selection tests; no real mounts, USB or target access."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('usb_app', str(
    ROOT / 'board/fastlinux/rootfs-overlay/usr/libexec/ninjalinux-usb-app'))
spec = importlib.util.spec_from_loader(loader.name, loader)
usb = importlib.util.module_from_spec(spec)
loader.exec_module(usb)


class USBTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        volume_patch = patch.object(usb, 'VOLUMES', self.root / 'cartridges')
        volume_patch.start()
        self.addCleanup(volume_patch.stop)
        (self.root / 'app.py').write_text('print("test")')
        self.data = dict(version=1, type='python3', program='app.py', args=['árvíz', 'a b', '$(touch nope)'])

    def write(self, data=None, root=None):
        root = root or self.root
        (root / 'autostart.json').write_text(json.dumps(data if data is not None else self.data))

    def test_python_argv_preserves_unicode_spaces_and_shell_literals(self):
        self.write()
        result = usb.manifest(self.root)
        self.assertEqual(result['argv'], ['/usr/bin/python3', str(self.root / 'app.py')] + self.data['args'])
        self.assertEqual(result['cwd'], str(self.root))

    def test_invalid_schema_and_paths_are_rejected(self):
        for changes in (dict(version=True), dict(writable='yes'), dict(type='shell'), dict(program='/bin/sh'),
                        dict(program='../escape'), dict(args='--unsafe'), dict(env={'PATH': '/bad'}),
                        dict(cwd='app.py'), dict(args=['bad\0arg'])):
            with self.subTest(changes=changes):
                self.write(self.data | changes)
                with self.assertRaises((ValueError, OSError)):
                    usb.manifest(self.root)

    def test_symlink_cannot_escape_volume(self):
        (self.root / 'escape').symlink_to('/etc/passwd')
        self.write(self.data | dict(program='escape'))
        with self.assertRaises(ValueError):
            usb.manifest(self.root)

    def test_native_requires_executable_and_has_no_shell(self):
        self.write(self.data | dict(type='native'))
        with self.assertRaises(ValueError):
            usb.manifest(self.root)
        (self.root / 'app.py').chmod(0o755)
        self.assertEqual(usb.manifest(self.root)['argv'][0], str(self.root / 'app.py'))

    def test_large_or_invalid_json_rejected(self):
        for content in ('{' * 2, ' ' * 16385):
            (self.root / 'autostart.json').write_text(content)
            with self.assertRaises(ValueError):
                usb.manifest(self.root)

    def boot(self, manifests):
        state = self.root / 'run'
        actions = []
        def command(argv):
            actions.append(argv)
            if argv[0] == 'mount':
                if argv[2] != 'vfat':
                    return False
                device, mountpoint = argv[-2:]
                if manifests.get(device) is not None:
                    volume = Path(mountpoint)
                    (volume / 'app.py').write_text('print("test")')
                    self.write(manifests[device], volume)
                return True
            return True
        with patch.object(usb, 'STATE', state), patch.object(usb, 'devices', return_value=list(manifests)), \
                patch.object(usb, 'run', side_effect=command), \
                patch.object(usb.time, 'monotonic', side_effect=[0, 4]):
            usb.prepare()
        return state, actions

    def test_unique_app_selected_and_volume_read_only(self):
        state, actions = self.boot({'/dev/sda1': self.data})
        selection = json.loads((state / 'selected.json').read_text())
        self.assertEqual(selection['root'], str(usb.VOLUMES / 'volume-sda1'))
        self.assertIn('volume-sda1/app.py', selection['argv'][1])
        self.assertIn('ro,nodev,nosuid,utf8=1', actions[0])
        self.assertFalse(any(a[0] == 'umount' for a in actions))
        # No hotplug rediscovery or rescanning on restart.
        with patch.object(usb, 'STATE', state), patch.object(usb, 'devices') as devices:
            usb.prepare()
            devices.assert_not_called()

    def test_missing_bad_or_multiple_apps_fall_back_and_unmount(self):
        for volumes in ({}, {'/dev/sda1': None}, {'/dev/sda1': dict(version=7)},
                        {'/dev/sda1': self.data, '/dev/sdb1': self.data}):
            with self.subTest(volumes=volumes):
                import shutil
                shutil.rmtree(self.root / 'run', ignore_errors=True)
                state, actions = self.boot(volumes)
                self.assertFalse((state / 'selected.json').exists())
                self.assertEqual(sum(a[0] == 'umount' for a in actions), len(volumes))

    def test_launch_redirects_state_to_ram_and_execs_exact_argv(self):
        state, _ = self.boot({'/dev/sda1': self.data})
        with patch.object(usb, 'STATE', state), patch.object(usb.os, 'chdir') as cd, \
                patch.object(usb.os, 'execv') as execute, patch.dict(os.environ, {}, clear=True):
            usb.launch()
            self.assertEqual(os.environ['HOME'], str(state / 'home'))
            self.assertEqual(os.environ['NINJALINUX_CARTRIDGE_ROOT'], str(usb.VOLUMES / 'volume-sda1'))
            self.assertEqual(os.environ['PYTHONDONTWRITEBYTECODE'], '1')
            self.assertTrue(os.environ['XDG_CONFIG_HOME'].startswith(str(state)))
            cd.assert_called_once_with(str(usb.VOLUMES / 'volume-sda1'))
            execute.assert_called_once_with('/usr/bin/python3',
                ['/usr/bin/python3', str(usb.VOLUMES / 'volume-sda1/app.py')] + self.data['args'])

    def test_discovery_excludes_sd_and_non_usb_disks_and_parent_disk(self):
        sys = self.root / 'sys'
        sys.mkdir()
        for name, usb_device, partition in [('sda', True, False), ('sda1', True, True),
                                           ('sdb', False, False), ('mmcblk0', True, False),
                                           ('sdc', True, False)]:
            target = self.root / ('usb1' if usb_device else 'ata1') / name
            target.mkdir(parents=True)
            if partition:
                (target / 'partition').touch()
            (sys / name).symlink_to(target)
        with patch.object(usb, 'SYS', sys):
            self.assertEqual(usb.devices(), ['/dev/sda1', '/dev/sdc'])

    def test_ext4_fallback_disables_journal_replay(self):
        state = self.root / 'ext4-run'
        actions = []
        def command(argv):
            actions.append(argv)
            if argv[0] == 'mount' and argv[2] == 'ext4':
                root = Path(argv[-1])
                (root / 'app.py').write_text('pass')
                self.write(root=root)
                return True
            return False
        with patch.object(usb, 'STATE', state), \
                patch.object(usb, 'devices', return_value=['/dev/sda1']), \
                patch.object(usb, 'run', side_effect=command), \
                patch.object(usb.time, 'monotonic', side_effect=[0, 4]):
            usb.prepare()
        self.assertIn('ro,nodev,nosuid,noload', actions[1])
        self.assertTrue((state / 'selected.json').exists())

    def test_writable_cartridge_persists_home_on_usb(self):
        state, actions = self.boot({'/dev/sda1': self.data | dict(writable=True)})
        self.assertEqual([a[0] for a in actions], ['mount', 'umount', 'mount'])
        self.assertIn('rw,nodev,nosuid,utf8=1', actions[-1])
        home = usb.VOLUMES / 'volume-sda1/.ninjalinux-state'
        self.assertTrue((home / 'config').is_dir())
        with patch.object(usb, 'STATE', state), patch.object(usb.os, 'chdir'), \
                patch.object(usb.os, 'execv'), patch.dict(os.environ, {}, clear=True):
            usb.launch()
            self.assertEqual(os.environ['HOME'], str(home))
            self.assertEqual(os.environ['XDG_CONFIG_HOME'], str(home / 'config'))

    def test_writable_mount_failure_falls_back(self):
        state = self.root / 'failed-run'
        def command(argv):
            if argv[0] == 'mount':
                if argv[4].startswith('rw'):
                    return False
                root = Path(argv[-1])
                (root / 'app.py').touch()
                self.write(self.data | dict(writable=True), root)
            return True
        with patch.object(usb, 'STATE', state), \
                patch.object(usb, 'devices', return_value=['/dev/sda1']), \
                patch.object(usb, 'run', side_effect=command), \
                patch.object(usb.time, 'monotonic', side_effect=[0, 4]):
            usb.prepare()
        self.assertFalse((state / 'selected.json').exists())

    def test_persistent_state_cannot_escape_usb(self):
        (self.root / '.ninjalinux-state').symlink_to('/tmp')
        with self.assertRaises(ValueError):
            usb.state_home(self.root)

    def test_mount_errors_are_bounded_and_report_failure(self):
        import subprocess
        for error in (OSError('missing mount'), subprocess.TimeoutExpired('mount', 3)):
            with patch.object(usb.subprocess, 'run', side_effect=error):
                self.assertFalse(usb.run(['mount']))


if __name__ == '__main__':
    unittest.main()
