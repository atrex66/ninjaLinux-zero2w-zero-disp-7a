# Windows remote access

[Magyar](windows-remote.hu.md) · [SSHFS](sshfs.md) · [HALShow](halshow.md)

The Pi is `192.168.0.234/24`; StepperNinja is `192.168.0.235`. Your computer must have a route to the Pi, normally on the same LAN. These instructions were checked against the official documentation; a Windows computer was not used for live acceptance testing.

For browser access without an SSH key, enable the optional
[on-demand file explorer](file-explorer.md) for `/data`.

## Terminal: PowerShell and OpenSSH

Open PowerShell and run:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519" root@192.168.0.234
```

Use a private key whose public key has already been installed on the Pi. Password login is disabled in this image. Verify the displayed host-key fingerprint through your existing trusted connection before accepting it. Windows needs the **OpenSSH Client**, not an SSH server. If `ssh` is missing, install the Client optional feature using Windows Settings. [Microsoft: SSH in Windows Terminal](https://learn.microsoft.com/en-us/windows/terminal/tutorials/ssh).

A newly generated PC key does not automatically grant access. Keep the working connection available while adding a new public key to `/data/ssh/authorized_keys`; preserve existing entries and permissions. Never copy a private key onto the Pi. [Microsoft: key management](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement).

## Files: WinSCP

1. Create an **SFTP** site: host `192.168.0.234`, port `22`, user `root`.
2. Advanced → SSH → Authentication: choose your private key. WinSCP can offer conversion of an OpenSSH key to its PuTTY format; keep the resulting private key on your PC.
3. Advanced → Environment → SFTP: enter `/data/tools/sftp-server` as the SFTP server. Disable SCP fallback for this custom server configuration.
4. Verify the host key and connect. The DRO is in `/data/apps/eszterga-dro/`; its persistent HAL file is `machine.hal`, and preferences are under `state/`.

The SFTP helper is installed on the current test Pi separately; an older base image may not contain it. An absent helper must be installed before SFTP/SSHFS will work. The root filesystem is normally read-only; `/data` is writable. Download a backup before editing. Do not overwrite a running application's files piecemeal or edit `state/generated.hal`, which the backend recreates.

Sources: [WinSCP custom SFTP server](https://winscp.net/eng/docs/ui_login_sftp), [WinSCP private-key settings](https://winscp.net/eng/docs/ui_login_authentication).

## Original HALShow through WSL2

WSL2 with WSLg can display the original Linux Tk HALShow on Windows. Microsoft specifies Windows 10 build 19044 or later, or Windows 11, for WSL GUI support. WSL1 does not provide this GUI integration. [Microsoft WSL GUI guide](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps).

In administrator PowerShell, for a new installation:

```powershell
wsl --install -d Ubuntu
wsl --update
```

Restart Windows if requested, then open Ubuntu and install the viewer prerequisites:

```sh
sudo apt update
sudo apt install git python3-tk bwidget openssh-client
```

Set up Pi SSH authentication **inside WSL**, including a trusted host-key entry. If you reuse your own Windows private key, copy it into WSL's `~/.ssh/` and set its permission to `600`; do not run it directly from `/mnt/c/` with permissive NTFS-derived permissions. A passphrase-protected key needs an SSH agent for the viewer's noninteractive connection. First prove that `ssh root@192.168.0.234` works in WSL.

Obtain the ninjaLinux repository using your GitHub access (currently private), then:

```sh
cd ninjaLinux-zero2w-zero-disp-7a
./components/automation-hal/tools/remote-halshow/run.sh \
  --host 192.168.0.234 --user root \
  --identity "$HOME/.ssh/id_ed25519" --known-hosts "$HOME/.ssh/known_hosts"
```

Follow the separate [HALShow guide](halshow.md) for Show/Watch and limitations. No local LinuxCNC installation is required. GitHub repository access and Pi SSH access are separate credentials. SSHFS inside WSL is a Linux-side mount; for ordinary Windows file browsing use WinSCP.

## What this provides

SSH gives a terminal, SFTP/SSHFS gives files, and HALShow gives read-only HAL diagnostics. The EGLFS image has no installed RDP/VNC desktop server; these connections do not mirror or remotely touch the DRO screen. Internet access requires a separately arranged secure network connection, such as a VPN.
