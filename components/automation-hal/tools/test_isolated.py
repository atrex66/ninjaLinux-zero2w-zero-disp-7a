#!/usr/bin/python3
"""Install/test/reinstall/remove actual .debs inside a disposable bwrap root."""
import argparse
from pathlib import Path
import subprocess
import os

parser = argparse.ArgumentParser()
parser.add_argument('rootfs', type=Path)
parser.add_argument('packages', type=Path)
args = parser.parse_args()
root = args.rootfs.resolve(strict=True)
packages = args.packages.resolve(strict=True)
project = Path(__file__).resolve().parents[1]
if root == Path('/') or not (root / 'var/lib/dpkg/status').exists():
    raise SystemExit('A disposable test rootfs is required')
debs = sorted(packages.glob('*_*.deb'))
names = [subprocess.check_output(['dpkg-deb', '-f', str(p), 'Package'], text=True).strip() for p in debs]
expected = {'automation-hal', 'automation-hal-dev', 'python3-automation-hal'}
if set(names) != expected or len(debs) != 3:
    raise SystemExit(f'Expected exactly the three Automation HAL packages, got {names}')


def isolated(uid, *command):
    subprocess.run(['bwrap', '--die-with-parent', '--unshare-all', '--uid', str(uid),
        '--gid', str(uid), '--cap-drop', 'ALL', '--bind', str(root), '/',
        '--ro-bind', str(packages), '/packages', '--ro-bind', str(project / 'tests'), '/test',
        '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--clearenv',
        '--setenv', 'PATH', '/usr/sbin:/usr/bin:/sbin:/bin',
        '--setenv', 'HOME', '/home/tester', '--setenv', 'LC_ALL', 'C',
        '--chdir', '/tmp', '--', *command], check=True)


files = ['/packages/' + p.name for p in debs]
# Verify the runtime alone: no SDK or Python HAL package may satisfy it accidentally.
isolated(0, '/bin/rm', '-f', '/opt/automation-hal/rtlib/sdk_probe.so')
isolated(0, 'dpkg', '--remove', 'automation-hal-dev', 'python3-automation-hal', 'automation-hal')
runtime = next('/packages/' + p.name for p, name in zip(debs, names) if name == 'automation-hal')
isolated(0, 'dpkg', '--install', runtime)
isolated(1000, '/usr/bin/python3', '/test/integration.py',
         'InstalledHAL.test_02_logic_thread_and_link_rules')
isolated(0, 'dpkg', '--install', *files)
isolated(0, 'dpkg', '--audit')
isolated(0, '/opt/automation-hal/bin/ahal', 'compile', '--install', '/test/sdk_probe.comp')
isolated(1000, '/usr/bin/python3', '/test/integration.py')
# Same-version reinstall exercises dpkg replacement without pretending it is a migration test.
isolated(0, 'dpkg', '--install', *files)
isolated(0, '/bin/rm', '/opt/automation-hal/rtlib/sdk_probe.so')
isolated(0, 'dpkg', '--remove', 'automation-hal-dev', 'python3-automation-hal', 'automation-hal')
if (root / 'opt/automation-hal/bin/halcmd').exists():
    raise SystemExit('Package removal left the HAL executable installed')
isolated(0, 'dpkg', '--install', *files)
isolated(0, '/opt/automation-hal/bin/ahal', 'compile', '--install', '/test/sdk_probe.comp')
isolated(1000, '/usr/bin/python3', '/test/integration.py')
print('PASS: install, functional tests, reinstall, remove, fresh install, functional tests')
