#!/usr/bin/env python3
"""Collect pinned sources for the external toolchain's target runtime libraries.

Hashes come from the exact Bootlin Buildroot revision used for this SDK.
The SDK itself is not part of the target SD image.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'artifacts/legal-info/toolchain-runtime-sources'
DEST.mkdir(parents=True, exist_ok=True)
COMMIT = '83947c7bb6158072bc2f52b58e90891cd3dc04a2'

def fetch(url, name, expected=None):
    target = DEST / name
    if not target.exists():
        temporary = target.with_name(target.name + '.partial')
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.rename(target)
    data = target.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected:
        algorithm, pinned_digest = expected
        assert hashlib.new(algorithm, data).hexdigest() == pinned_digest, f'{algorithm} mismatch: {name}'
    print('Verified', name, digest, flush=True)
    return dict(name=name, url=url, sha256=digest, bytes=target.stat().st_size)

archive = fetch(f'https://codeload.github.com/bootlin/buildroot-toolchains/tar.gz/{COMMIT}',
                f'bootlin-buildroot-{COMMIT}.tar.gz',
                ('sha256', '82cc11f696e549b01cc2c069d5d57101013848a9608250191e1d910d61b42f7a'))
hashes = {}
with tarfile.open(DEST / archive['name']) as source:
    for member in source.getmembers():
        if member.isfile() and member.name.endswith(('/package/gcc/gcc.hash', '/package/glibc/glibc.hash', '/linux/linux.hash')):
            for line in source.extractfile(member).read().decode().splitlines():
                fields = line.split()
                if len(fields) == 3 and fields[0] in ('sha256', 'sha512'):
                    hashes[fields[2]] = (fields[0], fields[1])

glibc = 'glibc-2.41-70-g1502c248d58cb99a203731707987a4342926e830.tar.gz'
downloads = [
    (f'https://toolchains.bootlin.com/downloads/releases/sources/{glibc[:-7]}/{glibc}', glibc),
    ('https://mirrors.kernel.org/gnu/gcc/gcc-14.3.0/gcc-14.3.0.tar.xz', 'gcc-14.3.0.tar.xz'),
    ('https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.4.296.tar.xz', 'linux-5.4.296.tar.xz'),
]
for _, name in downloads:
    assert name in hashes, f'Pinned SDK source hash missing: {name}'
with ThreadPoolExecutor(max_workers=3) as pool:
    futures = [pool.submit(fetch, url, name, hashes[name]) for url, name in downloads]
    records = [future.result() for future in futures]
records.insert(0, archive)
(DEST / 'provenance.json').write_text(json.dumps(dict(bootlin_buildroot_commit=COMMIT,
    toolchain='aarch64--glibc--stable-2025.08-1', files=records), indent=2) + '\n')
(DEST / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['name']}\n" for r in records))
# Extract license texts only; keep the complete archives alongside them.
for record in records[1:]:
    with tarfile.open(DEST / record['name']) as source:
        for member in source.getmembers():
            basename = Path(member.name).name
            if member.isfile() and basename in ('COPYING', 'COPYING.LIB', 'COPYING3', 'COPYING3.LIB', 'COPYING.RUNTIME', 'LICENSES'):
                if len(Path(member.name).parts) == 2:
                    out = DEST / 'licenses' / record['name'] / basename
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(source.extractfile(member).read())
