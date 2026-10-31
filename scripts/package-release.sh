#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-v0.1.0-rc1}"
REPO="${NINJALINUX_SOURCE_REPO:-$ROOT}"
RELEASE="$ROOT/artifacts/release-$VERSION"
python3 - "$ROOT" <<'PY'
import json,pathlib,sys
r=pathlib.Path(sys.argv[1])
report=json.loads((r/'artifacts/build-report.json').read_text())
assert report['physical_release_image_boot']=='passed'
assert json.loads((r/'artifacts/generic-image-acceptance/report.json').read_text())['validated']
assert json.loads((r/'artifacts/legal-info/toolchain-runtime-sources/provenance.json').read_text())['files']
PY
[ -z "$(git -C "$REPO" status --porcelain)" ] || { echo 'Commit source changes before packaging' >&2; exit 1; }
[ ! -e "$RELEASE" ] || { echo 'Release directory already exists' >&2; exit 1; }
mkdir -p "$RELEASE"
sha256sum -c "$ROOT/artifacts/fastlinux-rt.img.gz.sha256"
cp "$ROOT/artifacts/fastlinux-rt.img.gz" "$RELEASE/ninjalinux-zero2w-zero-disp-7a-rt-$VERSION.img.gz"
# Hardlink only the collected open-source material, never the workspace itself.
mkdir -p "$RELEASE/source-tree"
cp -al "$ROOT/artifacts/legal-info" "$RELEASE/source-tree/legal-info"
TREE="$RELEASE/source-tree/legal-info"
# SDK binaries are not on the SD image. Its runtime corresponding sources are
# provided under toolchain-runtime-sources, together with the SDK build system.
rm -rf "$TREE/sources/toolchain-external-bootlin-2025.08-1"
rm -f "$TREE/project-sources/ninjalinux-build-sources.tar.gz" "$TREE/SHA256SUMS" "$TREE/legal-info.sha256"
COMMIT="$(git -C "$REPO" rev-parse HEAD)"
git -C "$REPO" archive --format=tar.gz HEAD > "$TREE/project-sources/ninjalinux-$COMMIT.tar.gz"
cat > "$TREE/RELEASE-NOTES.txt" <<EOF
Project source commit: $COMMIT
The original Buildroot manifests and README are retained.
Their external Bootlin SDK binary archive is intentionally excluded here;
the SDK is not part of the target image. Corresponding target runtime sources,
license texts, hashes and SDK build scripts are in toolchain-runtime-sources/.
Buildroot's own source archive is in project-sources/.
SHA256SUMS describes the files actually present in this release bundle.
EOF
(cd "$TREE" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
tar -cf "$RELEASE/ninjalinux-corresponding-sources-$VERSION.tar" -C "$RELEASE/source-tree" legal-info
tar -tf "$RELEASE/ninjalinux-corresponding-sources-$VERSION.tar" > "$RELEASE/source-file-list.txt"
python3 - "$RELEASE/source-file-list.txt" <<'PY'
from pathlib import Path
import sys
names=Path(sys.argv[1]).read_text().splitlines()
assert not any(n.endswith(('/authorized_keys','/dropbear_ed25519_host_key','/id_ed25519')) for n in names)
assert not any('/backups/' in n or '/logs/' in n or 'pi-test-rt-hal.img' in n for n in names)
assert not any('toolchain-external-bootlin-2025.08-1/aarch64' in n for n in names)
PY
printf '%s\n' "$COMMIT" > "$RELEASE/SOURCE-COMMIT.txt"
(cd "$RELEASE" && sha256sum ./*.img.gz ./*.tar SOURCE-COMMIT.txt > SHA256SUMS)
echo "Release files prepared in $RELEASE"
