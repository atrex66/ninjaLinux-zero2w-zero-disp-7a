#!/usr/bin/python3
"""Run ONLY inside the disposable filesystem/PID/IPC namespace."""
import os
import ctypes
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

AHAL = '/opt/automation-hal/bin/ahal'
PREFIX = Path('/opt/automation-hal')


class InstalledHAL(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ahal-test-')
        self.work = Path(self.temp.name)
        self.running = []

    def tearDown(self):
        for process, log in self.running:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            log.close()
        self.temp.cleanup()

    def command(self, *args, ok=True):
        result = subprocess.run([AHAL, 'cmd', *args], text=True, capture_output=True, timeout=5)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def start(self, config=None, mode='sim', ini=None):
        config = config or PREFIX / 'share/automation-hal/examples/logic.hal'
        logpath = self.work / f'run-{len(self.running)}.log'
        log = logpath.open('w+')
        command = [AHAL, 'run', '--mode', mode]
        if ini:
            command += ['-i', str(ini)]
        process = subprocess.Popen([*command, str(config)], stdout=log, stderr=log)
        self.running.append((process, log))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            contents = logpath.read_text()
            if process.poll() is not None:
                self.fail('Startup failed: ' + contents)
            if 'configuration loaded' in contents:
                return process
            time.sleep(0.03)
        self.fail('Startup timed out: ' + logpath.read_text())

    def eventually(self, pin, expected):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.command('getp', pin).lower() == expected:
                return
            time.sleep(0.02)
        self.fail(f'{pin} did not become {expected}')

    def test_01_no_linuxcnc_dependency(self):
        self.assertFalse(Path('/usr/bin/halcmd').exists())
        self.assertFalse(Path('/usr/lib/linuxcnc').exists())
        result = subprocess.run(['/usr/bin/python3', '-c', 'import hal'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        status = Path('/var/lib/dpkg/status').read_text()
        self.assertNotIn('Package: linuxcnc', status)
        for binary in (PREFIX / 'bin/halcmd', PREFIX / 'bin/rtapi_app', PREFIX / 'lib/python/_hal.so'):
            output = subprocess.check_output(['ldd', str(binary)], text=True)
            self.assertNotIn('not found', output)
            self.assertNotIn('liblinuxcnc', output)

    def test_02_logic_thread_and_link_rules(self):
        self.start()
        self.command('setp', 'and2.0.in0', 'true')
        self.eventually('timedelay.0.out', 'false')
        self.command('setp', 'and2.0.in1', 'true')
        self.eventually('timedelay.0.out', 'true')
        self.command('setp', 'and2.0.in0', 'false')
        self.eventually('timedelay.0.out', 'false')
        self.assertIn('automation-thread', self.command('show', 'thread'))
        self.command('loadrt', 'or2', 'count=1')
        self.command('net', 'permitted', 'or2.0.out', ok=False)
        self.command('net', 'permitted', 'timedelay.0.on-delay', ok=False)

    def test_03_python_component(self):
        self.start()
        code = '''import hal
c = hal.component("python-probe")
c.newpin("value", hal.HAL_FLOAT, hal.HAL_OUT)
c.ready()
c["value"] = 12.5
assert hal.get_value("python-probe.value") == 12.5
c.exit()
'''
        subprocess.run([AHAL, 'python', '-c', code], check=True, timeout=5)
        self.command('getp', 'python-probe.value', ok=False)

    def test_04_sdk_realtime_and_userspace(self):
        self.start()
        comp = self.work / 'sdk_probe.comp'
        shutil.copyfile(Path(__file__).with_name('sdk_probe.comp'), comp)
        build = subprocess.run([AHAL, 'compile', '--compile', str(comp)], cwd=self.work,
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        self.assertTrue((self.work / 'sdk_probe.so').is_file())
        # The test harness installs the same fixture as root before this unprivileged test.
        self.command('loadrt', 'sdk_probe', 'count=1')
        self.command('addf', 'sdk-probe.0', 'automation-thread')
        time.sleep(0.05)
        self.assertGreater(int(self.command('getp', 'sdk-probe.0.ticks')), 0)
        cfile = self.work / 'sdk_user.c'
        cfile.write_text('''#include "hal.h"
int main(void) {
    int id = hal_init("sdk-user");
    if (id < 0) return 1;
    hal_float_t **p = hal_malloc(sizeof(*p));
    if (!p || hal_pin_float_new("sdk-user.value", HAL_OUT, p, id)) return 2;
    **p = 4.25;
    if (hal_ready(id)) return 3;
    return hal_exit(id);
}
''')
        build = subprocess.run([AHAL, 'compile', '--compile', '--userspace', str(cfile)],
                               cwd=self.work, capture_output=True, text=True, timeout=30)
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        subprocess.run([str(self.work / 'sdk_user')], check=True, timeout=5)

    def test_05_ini_configuration(self):
        ini = self.work / 'test.ini'
        ini.write_text('[SCALE]\nGAIN = 3.5\n')
        config = self.work / 'test.hal'
        config.write_text('''loadrt threads name1=test-thread period1=1000000
loadrt scale count=1
setp scale.0.gain [SCALE]GAIN
setp scale.0.in 2
addf scale.0 test-thread
start
''')
        self.start(config, ini=ini)
        self.eventually('scale.0.out', '7')

    def test_06_single_owner_and_restart(self):
        process = self.start()
        duplicate = subprocess.run([AHAL, 'run', '--mode', 'sim',
            str(PREFIX / 'share/automation-hal/examples/logic.hal')], capture_output=True, timeout=5)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIsNone(process.poll())
        process.terminate()
        self.assertEqual(process.wait(timeout=10), 0)
        self.assertFalse(Path('/tmp/automation-hal-1000/control.sock').exists())
        self.start()

    def test_07_failed_config_cleans_up(self):
        config = self.work / 'bad.hal'
        config.write_text('loadrt threads name1=test-thread period1=1000000\ninvalid-command\n')
        failed = subprocess.run([AHAL, 'run', '--mode', 'sim', str(config)],
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('configuration failed', failed.stderr)
        self.start()

    def test_08_runtime_crash_is_reported(self):
        process = self.start()
        children = Path(f'/proc/{process.pid}/task/{process.pid}/children').read_text().split()
        self.assertTrue(children)
        os.kill(int(children[0]), signal.SIGKILL)
        self.assertNotEqual(process.wait(timeout=10), 0)
        self.start()

    def test_09_realtime_does_not_fall_back(self):
        result = subprocess.run([AHAL, 'run', '--mode', 'realtime',
            str(PREFIX / 'share/automation-hal/examples/logic.hal')], capture_output=True,
            text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('simulation (SCHED_OTHER)', result.stderr)
        self.start()

    def test_10_interrupt_waiting_userspace_component(self):
        config = self.work / 'wait.hal'
        config.write_text('loadrt threads name1=test-thread period1=1000000\n'
                          'loadusr -Wn never-ready /bin/sleep 60\n')
        log = (self.work / 'wait.log').open('w+')
        process = subprocess.Popen([AHAL, 'run', '--mode', 'sim', str(config)], stdout=log, stderr=log)
        self.running.append((process, log))
        time.sleep(0.5)
        process.terminate()
        process.wait(timeout=10)
        for entry in Path('/proc').iterdir():
            if entry.name.isdigit():
                try:
                    self.assertNotEqual((entry / 'comm').read_text().strip(), 'sleep')
                except (FileNotFoundError, ProcessLookupError):
                    pass
        self.start()

    def test_11_original_linuxcnc_ipc_keys_untouched(self):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.shmget.argtypes = [ctypes.c_int, ctypes.c_size_t, ctypes.c_int]
        libc.shmat.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        libc.shmat.restype = ctypes.c_void_p
        libc.shmdt.argtypes = [ctypes.c_void_p]
        libc.shmctl.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        segments = []
        try:
            for key in (0x48414C32, 0x48484C34, 0x90280A48):
                ident = libc.shmget(ctypes.c_int(key), 128, 0o1000 | 0o2000 | 0o600)
                self.assertGreaterEqual(ident, 0)
                address = libc.shmat(ident, None, 0)
                self.assertNotEqual(address, ctypes.c_void_p(-1).value)
                ctypes.memmove(address, b'original-key-sentinel', 22)
                segments.append((key, ident, address))
            process = self.start()
            self.command('setp', 'and2.0.in0', 'true')
            process.terminate()
            self.assertEqual(process.wait(timeout=10), 0)
            for key, ident, address in segments:
                self.assertEqual(libc.shmget(ctypes.c_int(key), 128, 0o600), ident)
                self.assertEqual(ctypes.string_at(address, 21), b'original-key-sentinel')
        finally:
            for _, ident, address in segments:
                libc.shmdt(address)
                libc.shmctl(ident, 0, None)


if __name__ == '__main__':
    assert os.getuid() == 1000, 'Use the isolated unprivileged test namespace'
    unittest.main(verbosity=2)
