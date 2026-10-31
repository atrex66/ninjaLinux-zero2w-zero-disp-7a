# Remote original HALShow

English · [Magyar](halshow.hu.md) · [Windows / WSL](windows-remote.md#original-halshow-through-wsl2)

This is the original Tcl/Tk HALShow from the project's LinuxCNC source, with a read-only SSH adapter. The GUI runs on the PC and observes the already running standalone Automation HAL on the Pi. [SSHFS](sshfs.md) is optional and is not used for the live connection.

## PC setup and connection

Debian/Ubuntu dependencies:

```sh
sudo apt install python3 python3-tk bwidget openssh-client
```

From the ninjaLinux repository root:

```sh
./components/automation-hal/tools/remote-halshow/run.sh
```

The connection dialog accepts host/IP, SSH user, SSH port, private key and known-hosts file. Current appliance: `192.168.0.234`, user `root`, port `22`. Establish key-based SSH login and verify the host key before starting; password prompts are disabled in the viewer. A passphrase-protected key must be available through a running SSH agent.

Explicit command-line equivalent using your own SSH files:

```sh
./components/automation-hal/tools/remote-halshow/run.sh \
  --host 192.168.0.234 --user root --port 22 \
  --identity "$HOME/.ssh/id_ed25519" \
  --known-hosts "$HOME/.ssh/known_hosts"
```

The target needs `/opt/automation-hal/libexec/halshow_agent.py`, Python 3 and the running private `ahal` runtime. The agent was verified on the current Pi on 2026-10-31. It is included by the updated Automation HAL install rules; the original v0.1.0-rc1 image predates this addition. Install the updated runtime/agent on a fresh card first.

## Using the viewer

Expand the Components, Pins, Parameters, Signals, Functions or Threads tree. **Show** displays the selected object; select the **Watch** tab, then click a pin/signal/parameter leaf name in the tree to add it to the watch list. Watch shows changing numeric values and bit LEDs. Search/filter narrows the tree. Saved watchlists/preferences are local to the PC and target, under the tool's ignored `state/` directory.

The command field accepts read queries such as `show pin`, `list pin`, `getp NAME` and `gets NAME`. `show`, `list`, `getp`, `gets`, `ptype` and `stype` are supported; writes and loading/restarting components are rejected. This does not start a second HAL or connect to a local LinuxCNC installation.

Pins/signals/parameters refresh every 500 ms by default; structural metadata every 3 seconds. Short pulses can fall between snapshots: use a HAL latch/counter/sampler for pulse capture. This is not an oscilloscope or a latency measurement. Disconnected/stale values turn grey/unavailable and SSH reconnects automatically.

Closing HALShow closes only its SSH agent session. It leaves the target application and HAL running. No permanent server service or additional TCP port is needed.

## Troubleshooting

- **Permission denied:** check user, private key, the matching authorized public key and SSH-agent availability.
- **Host key verification failed:** verify the target fingerprint and select the correct known-hosts file; do not disable checking.
- **Agent missing:** install the updated runtime/agent at the exact path above.
- **No running private HAL:** the application/HAL owner must already be running as the expected `ahal` user.

[Implementation, tests, original-source provenance and GPL license](../components/automation-hal/tools/remote-halshow/README.md).
