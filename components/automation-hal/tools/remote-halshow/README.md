# Remote original HALShow

The original Tcl/Tk HALShow copied unchanged from the user's LinuxCNC 2.9.10 source tree, with an SSH snapshot-backed HAL adapter. See [Hungarian instructions](README.hu.md) and `provenance.json`.

Run `./run.sh` for the IP/SSH connection dialog, or `./run.sh --host 192.168.0.234` for the current Pi. The GUI computer needs Python 3, Tk, BWidget and an OpenSSH client; a local LinuxCNC installation is unnecessary. SSH uses existing key authentication and strictly checks known host keys.

The Automation HAL runtime installs `remote_agent.py` as `/opt/automation-hal/libexec/halshow_agent.py`. It is already installed on the current Pi. Root SSH sessions drop to the private runtime's `ahal` user. The agent only runs during the SSH session, uses housekeeping CPUs 0–1, starts no new HAL and opens no additional network port.

The original object tree, Show/Watch tabs, filtering and saved watchlists are preserved. Only `show`, `list`, `getp`, `gets`, `ptype` and `stype` are supported. Write controls are suppressed, and the remote side only executes fixed `halcmd show` queries. Local LinuxCNC shared memory is never opened.

Default snapshots arrive every 500 ms; component/function/thread metadata is refreshed every 3 seconds. This is state monitoring: use a HAL counter/latch/sampler for short pulses. Stale values are greyed out; SSH reconnects automatically. Per-target preferences stay in the ignored local `state/` directory.

Tests: `python3 tests/test_model.py`; opt-in read-only live test: `python3 tests/live_connection.py`; GUI test: `./run.sh --host 192.168.0.234 --smoke`.

The original authorship headers and GPL-2.0 license are retained in `COPYING` and the vendored files.
