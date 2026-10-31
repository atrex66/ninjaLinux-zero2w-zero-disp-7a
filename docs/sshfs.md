# SSHFS: remote files from Linux

English · [Magyar](sshfs.hu.md) · [Windows access](windows-remote.md)

SSHFS mounts the Pi filesystem as a directory on your computer. It is for file access. [HALShow](halshow.md) separately displays live HAL objects and does not need an SSHFS mount.

## Before mounting

The PC needs `sshfs`, a working SSH key login to `root@192.168.0.234:22`, and the Pi's verified host key. On Debian/Ubuntu, install the client with `sudo apt install sshfs`. Use the private key corresponding to the public key provisioned on the SD card; see the [first-boot instructions](../README.md#first-boot).

First establish ordinary SSH access, checking the host fingerprint against a trusted record when asked:

```sh
ssh -i "$HOME/.ssh/id_ed25519" -o IdentitiesOnly=yes root@192.168.0.234
```

Leave that shell with `exit`. The current appliance has the SFTP helper at `/data/tools/sftp-server`; SSHFS must explicitly select it because the minimal SSH server does not provide the usual SFTP subsystem automatically.

```sh
ssh -i "$HOME/.ssh/id_ed25519" -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes root@192.168.0.234 \
  'test -x /data/tools/sftp-server'
```

This helper was verified on the working Pi on 2026-10-31. It was deployed separately and is **not guaranteed to be present in the original v0.1.0-rc1 image**. A missing helper must be installed for the target architecture before mounting; SSH working alone does not imply SFTP support.

## Read-only mount

Create an empty local directory. Check `mountpoint` first and continue only if it is not already mounted; do not stack mounts on the same directory.

```sh
mkdir -p "$HOME/mnt/ninjaLinux"
mountpoint "$HOME/mnt/ninjaLinux"
```

```sh
sshfs root@192.168.0.234:/ "$HOME/mnt/ninjaLinux" \
  -o ro,reconnect,idmap=user \
  -o IdentityFile="$HOME/.ssh/id_ed25519" \
  -o IdentitiesOnly=yes,StrictHostKeyChecking=yes \
  -o ServerAliveInterval=15,ServerAliveCountMax=3 \
  -o sftp_server=/data/tools/sftp-server
```

Open `$HOME/mnt/ninjaLinux` in the PC file manager. `/data` is persistent; the Pi root filesystem is normally read-only. The mount's `ro` option also prevents writes to `/data` through this view.

## Unmount and troubleshoot

Close files and terminals using the mount, then:

```sh
fusermount3 -u "$HOME/mnt/ninjaLinux"
```

On older FUSE installations the command may be `fusermount -u`. If mounting fails, test ordinary SSH first. “Subsystem request failed” or an immediate disconnect commonly means the custom SFTP helper is missing or was not selected. An empty mount directory alone does not prove the mount succeeded; check `mountpoint`/`findmnt`.

For intentional editing, mount only the application's writable directory and omit `ro`. An SSHFS mount neither reloads HAL nor restarts an application after file changes. Never put private SSH keys or per-machine runtime state in Git.

## Mount only the writable DRO directory

Use a different empty mount point. This permits file edits; save a backup first and avoid changing a running app piecemeal.

```sh
mkdir -p "$HOME/mnt/EsztergaDRO"
mountpoint "$HOME/mnt/EsztergaDRO"
# Continue only if not mounted / Csak akkor folytasd, ha nincs csatolva.
sshfs root@192.168.0.234:/data/apps/eszterga-dro "$HOME/mnt/EsztergaDRO" \
  -o reconnect,idmap=user,IdentitiesOnly=yes,StrictHostKeyChecking=yes \
  -o IdentityFile="$HOME/.ssh/id_ed25519" \
  -o sftp_server=/data/tools/sftp-server
# Unmount / Leválasztás:
fusermount3 -u "$HOME/mnt/EsztergaDRO"
```
