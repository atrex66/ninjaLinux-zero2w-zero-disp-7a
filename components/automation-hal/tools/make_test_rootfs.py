#!/usr/bin/python3
"""Build a disposable Debian test root from package archives, without host installs.

This is a minimal test fixture, not a bootable Debian installation. Dependency
archives are extracted with their dpkg metadata; our own packages are subsequently
installed, upgraded and removed with real dpkg inside an isolated namespace.
"""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import hashlib
import tarfile
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--download', action='store_true')
args = parser.parse_args()
work = args.directory.resolve()
work.mkdir(parents=True, exist_ok=True)
archives = work / 'archives'
archives.mkdir(exist_ok=True)
status = work / 'empty-status'
status.write_text('')
packages = ['bash', 'coreutils', 'dpkg', 'python3', 'python3-yapps', 'gcc', 'make',
            'binutils', 'libc6-dev', 'libudev1', 'libstdc++6', 'libc-bin',
            'dash', 'diffutils', 'mawk', 'sed', 'grep', 'findutils', 'gzip']
if args.download:
    plan = subprocess.check_output(['apt-get', '-s', '-o', f'Dir::State::status={status}',
        '-o', 'Debug::NoLocking=1', '--no-install-recommends', 'install', *packages], text=True)
    names = [line.split()[1] for line in plan.splitlines() if line.startswith('Inst ')]
    subprocess.run(['apt-get', 'download', *names], cwd=archives, check=True)
    (work / 'apt-plan.txt').write_text(plan)

root = work / 'rootfs'
if root.exists():
    raise SystemExit(f'{root} already exists; choose a new directory')
root.mkdir()
# Debian merged-/usr layout, also used by current arm64 images.
for name in ('bin', 'sbin', 'lib', 'lib64'):
    (root / 'usr' / name).mkdir(parents=True, exist_ok=True)
    (root / name).symlink_to('usr/' + name)
db = root / 'var/lib/dpkg'
(db / 'info').mkdir(parents=True)
(db / 'updates').mkdir()
entries = []
manifest = []
for deb in sorted(archives.glob('*.deb')):
    subprocess.run(['dpkg-deb', '-x', str(deb), str(root)], check=True)
    control = subprocess.check_output(['dpkg-deb', '-f', str(deb)], text=True).strip()
    entries.append(control + '\nStatus: install ok installed\n')
    fields = dict(line.split(': ', 1) for line in control.splitlines() if ': ' in line and not line.startswith(' '))
    dbname = fields['Package']
    if fields.get('Multi-Arch') == 'same':
        dbname += ':' + fields['Architecture']
    data = subprocess.Popen(['dpkg-deb', '--fsys-tarfile', str(deb)], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=data.stdout, mode='r|') as archive:
        paths = ['/' + member.name.removeprefix('./').rstrip('/') for member in archive]
    data.stdout.close()
    if data.wait():
        raise RuntimeError(f'Cannot list {deb}')
    (db / 'info' / (dbname + '.list')).write_text('\n'.join(paths) + '\n')
    with tempfile.TemporaryDirectory(dir=work) as temp:
        subprocess.run(['dpkg-deb', '-e', str(deb), temp], check=True)
        checksums = Path(temp) / 'md5sums'
        if checksums.exists():
            shutil.copy2(checksums, db / 'info' / (dbname + '.md5sums'))
    manifest.append({'archive': deb.name, 'sha256': hashlib.sha256(deb.read_bytes()).hexdigest()})
if not entries:
    raise SystemExit('No dependency archives; run with --download first')
(db / 'status').write_text('\n'.join(entries))
(db / 'available').write_text('')
# These essential-system alternatives are normally set by maintainer scripts.
for name, target in [('sh', 'dash'), ('awk', 'mawk'), ('cc', 'gcc')]:
    path = root / 'usr/bin' / name
    if not path.exists():
        path.unlink(missing_ok=True)
        path.symlink_to(target)
for name in ('tmp', 'proc', 'dev', 'run', 'etc', 'test', 'packages', 'home/tester', 'opt'):
    (root / name).mkdir(parents=True, exist_ok=True)
(root / 'tmp').chmod(0o1777)
(root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\ntester:x:1000:1000:tester:/home/tester:/bin/bash\n')
(root / 'etc/group').write_text('root:x:0:\ntester:x:1000:\n')
(root / 'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files\n')
(root / 'etc/ld.so.conf').write_text('include /etc/ld.so.conf.d/*.conf\n')
(work / 'dependency-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(root)
