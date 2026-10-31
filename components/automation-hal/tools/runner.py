#!/usr/bin/python3
"""Foreground owner of one private HAL session per Unix user."""
import argparse
import ctypes
import fcntl
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from cpu_layout import apply_role, selected_config

PREFIX = Path(os.environ['AHAL_PREFIX'])


def clean_shared_memory():
    """Remove only detached, caller-owned segments in our translated key space.

    Must hold owner.lock. Never remove a live attachment or any LinuxCNC key.
    External modules with their own keys must release their own resources.
    """
    keys = {0x48414C32, 0x48484C34}
    keys.update(0x48535430 + i for i in range(8))
    keys.update(0x48534130 + i for i in range(8))
    keys = {key ^ 0x41480000 for key in keys}
    libc = ctypes.CDLL(None, use_errno=True)
    libc.shmctl.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    libc.shmctl.restype = ctypes.c_int
    lines = Path('/proc/sysvipc/shm').read_text().splitlines()
    headers = lines[0].split()
    for line in lines[1:]:
        segment = dict(zip(headers, line.split()))
        if (int(segment['key']) & 0xffffffff) not in keys:
            continue
        if int(segment['uid']) != os.getuid() or int(segment['cuid']) != os.getuid():
            raise RuntimeError('Private HAL shared memory belongs to another user')
        if int(segment['nattch']):
            raise RuntimeError('A process still uses private HAL shared memory; refusing to reset it')
        if libc.shmctl(int(segment['shmid']), 0, None) != 0:  # IPC_RMID
            raise OSError(ctypes.get_errno(), 'Cannot remove detached HAL shared memory')


def runtime_environment():
    directory = Path('/tmp') / f'automation-hal-{os.getuid()}'
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError(f'Unsafe runtime directory: {directory}')
    env = os.environ.copy()
    env.pop('RTAPI_UID', None)
    env['RTAPI_FIFO_PATH'] = str(directory / 'control.sock')
    env['HAL_RTMOD_DIR'] = str(PREFIX / 'rtlib')
    return directory, env


def main():
    parser = argparse.ArgumentParser(description='Standalone automation HAL')
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('run', help='own and supervise a HAL session')
    run.add_argument('--mode', choices=('sim', 'realtime'), required=True)
    run.add_argument('-i', '--ini')
    run.add_argument('--cpu-config', type=Path, help='shared HAL/UI CPU layout JSON')
    run.add_argument('configuration', type=Path)
    for name in ('cmd', 'compile', 'python'):
        commands.add_parser(name, add_help=False).add_argument('args', nargs=argparse.REMAINDER)
    args, remaining = parser.parse_known_args()
    if args.command == 'run' and remaining:
        parser.error('unrecognized arguments: ' + ' '.join(remaining))
    # Keep all arguments, including switches, in the original order for pass-through commands.
    if args.command == 'compile':
        target = str(PREFIX / 'bin/halcompile')
        os.execv(target, [target, *sys.argv[2:]])
    if args.command == 'run':
        cpu_config = selected_config(args.cpu_config)
        if cpu_config is not None:
            apply_role('hal', cpu_config)
    directory, env = runtime_environment()
    if args.command == 'python':
        os.execve('/usr/bin/python3', ['python3', *sys.argv[2:]], env)
    if args.command == 'cmd':
        if not Path(env['RTAPI_FIFO_PATH']).exists():
            raise RuntimeError('No active Automation HAL session for this user')
        os.execve(str(PREFIX / 'bin/halcmd'), ['halcmd', *sys.argv[2:]], env)
    if os.getuid() == 0:
        raise RuntimeError('Run HAL as a regular user, not root')
    configuration = args.configuration.resolve(strict=True)
    fd = os.open(directory / 'owner.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('An Automation HAL session is already running for this user')
        socket = Path(env['RTAPI_FIFO_PATH'])
        if socket.exists():
            # Do not guess whether a directly started server still owns this socket.
            raise RuntimeError(f'Existing runtime socket requires inspection: {socket}')
        clean_shared_memory()
        env['AHAL_MODE'] = args.mode
        stopping = False

        def stop(signum, frame):
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        runtime = subprocess.Popen([str(PREFIX / 'bin/rtapi_app')], env=env, process_group=0)
        result = 0
        try:
            deadline = time.monotonic() + 10
            while not socket.exists():
                if runtime.poll() is not None:
                    raise RuntimeError(f'Runtime startup failed ({runtime.returncode})')
                if stopping or time.monotonic() > deadline:
                    raise RuntimeError('Runtime startup interrupted or timed out')
                time.sleep(0.02)
            command = [str(PREFIX / 'bin/halcmd')]
            if args.ini:
                command += ['-i', str(Path(args.ini).resolve(strict=True))]
            command += ['-f', str(configuration)]
            loader = subprocess.Popen(command, env=env, cwd=configuration.parent,
                                      process_group=runtime.pid)
            while loader.poll() is None:
                if stopping or runtime.poll() is not None:
                    raise RuntimeError('Configuration loading interrupted')
                time.sleep(0.05)
            if loader.returncode:
                raise RuntimeError(f'HAL configuration failed ({loader.returncode})')
            print('Automation HAL: configuration loaded', flush=True)
            while not stopping:
                if runtime.poll() is not None:
                    raise RuntimeError(f'Runtime exited unexpectedly ({runtime.returncode})')
                time.sleep(0.1)
        except (RuntimeError, OSError) as exc:
            print(f'Automation HAL: {exc}', file=sys.stderr)
            result = 1
        finally:
            if runtime.poll() is None and socket.exists():
                for command in ([str(PREFIX / 'bin/halcmd'), 'stop'],
                                [str(PREFIX / 'bin/halcmd'), 'unload', 'all'],
                                [str(PREFIX / 'bin/rtapi_app'), 'exit']):
                    if runtime.poll() is not None:
                        break
                    try:
                        subprocess.run(command, env=env, timeout=3, check=False,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except subprocess.TimeoutExpired:
                        break
            try:
                os.killpg(runtime.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                runtime.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(runtime.pid, signal.SIGKILL)
                runtime.wait()
            # All children launched by the configuration share the runtime process group.
            try:
                os.killpg(runtime.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            socket.unlink(missing_ok=True)
            # SIGKILL releases attachments asynchronously; wait briefly for group members.
            deadline = time.monotonic() + 2
            while True:
                try:
                    clean_shared_memory()
                    break
                except RuntimeError as exc:
                    if time.monotonic() >= deadline:
                        print(f'Automation HAL: cleanup: {exc}', file=sys.stderr)
                        result = 1
                        break
                    time.sleep(0.02)
        return result


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        sys.exit(f'Automation HAL: {exc}')
