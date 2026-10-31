"""On-Pi paced USB/Ethernet load; send stdout over SSH to a /dev/null sink.

70 MiB at about 1 MiB/s, spanning probe seconds 55..125. Never touch devices
or files with the payload. Writes timing, counters and byte count separately.
"""
import argparse
import json
from pathlib import Path
import sys
import time

p = argparse.ArgumentParser()
p.add_argument("folder", type=Path)
args = p.parse_args()
assert not (args.folder / "network-load.json").exists()
deadline = time.monotonic() + 30
while True:
    try:
        conditions = json.loads((args.folder / "conditions.json").read_text())
        began = conditions["probe_start_monotonic"]
        break
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        if time.monotonic() > deadline:
            raise RuntimeError("Probe did not start")
        time.sleep(.2)
assert not conditions.get("success")
assert time.monotonic() - began < 50, "Load launch missed its preparation window"
while time.monotonic() < began + 55:
    time.sleep(max(0, min(.2, began + 55 - time.monotonic())))
record = dict(start_monotonic=time.monotonic(), probe_start_monotonic=began,
              expected_bytes=70 * 1024 * 1024, target_bytes_per_second=1024 * 1024,
              interrupts_before=Path("/proc/interrupts").read_text(),
              network_before=Path("/proc/net/dev").read_text())
chunk = bytes(65536)
sent = 0
for block in range(70 * 16):
    when = began + 55 + block / 16
    delay = when - time.monotonic()
    if delay > 0:
        time.sleep(delay)
    sys.stdout.buffer.write(chunk)
    sys.stdout.buffer.flush()
    sent += len(chunk)
record.update(end_monotonic=time.monotonic(), sent_bytes=sent,
              interrupts_after=Path("/proc/interrupts").read_text(),
              network_after=Path("/proc/net/dev").read_text())
(args.folder / "network-load.json").write_text(json.dumps(record, indent=2) + "\n")
print("NETWORK_LOAD_COMPLETE", sent, "bytes", file=sys.stderr, flush=True)
