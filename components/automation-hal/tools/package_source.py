#!/usr/bin/python3
"""Create a self-contained source tarball, excluding builds and test artifacts."""
import gzip
from pathlib import Path
import tarfile

project = Path(__file__).resolve().parents[1]
destination = project / 'dist'
destination.mkdir(exist_ok=True)
output = destination / 'automation-hal-0.1.0-source.tar.gz'
with output.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
    with tarfile.open(fileobj=zipped, mode='w') as archive:
        for path in sorted(project.rglob('*')):
            relative = path.relative_to(project)
            if (relative.parts[0].startswith('build') or relative.parts[0] in ('dist', '.git')
                    or '__pycache__' in relative.parts or path.suffix == '.pyc' or not path.is_file()):
                continue
            info = archive.gettarinfo(str(path), 'automation-hal-0.1.0/' + str(relative))
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = 'root'
            with path.open('rb') as contents:
                archive.addfile(info, contents)
print(output)
