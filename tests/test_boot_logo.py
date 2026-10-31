"""Host-only image conversion and simulated splash lifecycle tests."""
import importlib.util
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prepare_logo', ROOT / 'scripts/prepare-boot-logo.py')
logo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(logo)
HELPER = ROOT / 'board/fastlinux/rootfs-overlay/usr/libexec/ninjalinux-boot-logo'


class LogoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_png_centered_preserves_aspect_and_flattens_alpha(self):
        source = self.root / 'source.png'
        Image.new('RGBA', (100, 100), (255, 0, 0, 128)).save(source)
        output = self.root / 'logo.png'
        logo.prepare(source, output)
        with Image.open(output) as result:
            self.assertEqual(result.size, (1024, 600))
            self.assertEqual(result.mode, 'RGB')
            self.assertEqual(result.getpixel((0, 0)), (0, 0, 0))
            self.assertEqual(result.getpixel((512, 300)), (128, 0, 0))
            self.assertEqual(result.getpixel((210, 300)), (0, 0, 0))

    def test_invalid_missing_or_fake_png_returns_failure_without_output(self):
        output = self.root / 'output.png'
        for source in ('missing.png', 'bad.png'):
            path = self.root / source
            if source == 'bad.png':
                path.write_text('this is not a PNG')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-boot-logo.py'),
                                     str(path), str(output)], capture_output=True, text=True, timeout=2)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Boot logo omitted:', result.stderr)
            self.assertFalse(output.exists())

    @unittest.skipUnless(shutil.which('rsvg-convert') or shutil.which('convert') or shutil.which('magick'),
                         'No host SVG renderer')
    def test_svg_converts_to_opaque_target_size(self):
        output = self.root / 'logo.png'
        logo.prepare(ROOT / 'examples/boot-logo/ninjalinux.svg', output)
        with Image.open(output) as result:
            self.assertEqual(result.size, (1024, 600))
            self.assertEqual(result.mode, 'RGB')
            self.assertIsNotNone(result.getbbox())

    def environment(self, fake_status=None):
        fb = self.root / 'fb0'
        fb.touch()
        fake = self.root / 'psplash'
        fake.write_text('#!' + sys.executable + '\nimport os,time\nfrom pathlib import Path\n'
                        'Path(os.environ["TEST_STARTED"]).write_text(" ".join(__import__("sys").argv[1:]))\n'
                        + ('raise SystemExit(' + str(fake_status) + ')\n' if fake_status is not None
                           else 'time.sleep(10)\n'))
        fake.chmod(0o755)
        return dict(os.environ, NINJALINUX_SPLASH_STATE=str(self.root / 'state'),
                    NINJALINUX_PSPLASH=str(fake), NINJALINUX_SPLASH_FB=str(fb),
                    TEST_STARTED=str(self.root / 'started'))

    def start(self, env):
        process = subprocess.Popen(['sh', str(HELPER), 'run'], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        def cleanup():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1)
        self.addCleanup(cleanup)
        return process

    def wait_for(self, path):
        deadline = time.monotonic() + 1
        while not path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(path.exists())

    def test_start_and_stop_before_qt_reaps_writer_and_prevents_restart(self):
        env = self.environment()
        process = self.start(env)
        self.wait_for(self.root / 'started')
        self.assertEqual((self.root / 'started').read_text(), '-n')
        result = subprocess.run(['sh', str(HELPER), 'stop'], env=env, timeout=1)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(process.wait(timeout=1), 0)
        self.assertFalse((self.root / 'state/pid').exists())
        (self.root / 'started').unlink()
        subprocess.run(['sh', str(HELPER), 'run'], env=env, check=True, timeout=1)
        self.assertFalse((self.root / 'started').exists())

    def test_failed_splash_does_not_hold_boot(self):
        env = self.environment(fake_status=1)
        process = self.start(env)
        self.assertEqual(process.wait(timeout=1), 0)
        self.assertFalse((self.root / 'state/pid').exists())

    def test_stop_while_waiting_for_missing_framebuffer(self):
        env = self.environment()
        Path(env['NINJALINUX_SPLASH_FB']).unlink()
        process = self.start(env)
        self.wait_for(self.root / 'state/pid')
        subprocess.run(['sh', str(HELPER), 'stop'], env=env, check=True, timeout=1)
        self.assertEqual(process.wait(timeout=1), 0)
        self.assertFalse((self.root / 'started').exists())

    def test_stop_before_early_init_cannot_start_late_logo(self):
        env = self.environment()
        subprocess.run(['sh', str(HELPER), 'stop'], env=env, check=True, timeout=1)
        process = self.start(env)
        self.assertEqual(process.wait(timeout=1), 0)
        self.assertFalse((self.root / 'started').exists())


if __name__ == '__main__':
    unittest.main()
