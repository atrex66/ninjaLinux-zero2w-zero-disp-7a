"""Real loopback HTTP and isolated temporary-directory explorer tests."""
import importlib.machinery
import importlib.util
import http.client
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader('explorer', str(
    ROOT / 'board/fastlinux/rootfs-overlay/usr/libexec/ninjalinux-file-explorer'))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
explorer = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(explorer)
ASSETS = ROOT / 'board/fastlinux/rootfs-overlay/usr/share/ninjalinux-file-explorer'
TOKEN = 'temporary-test-token-never-deployed'


class FilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = explorer.Files(self.root)
        self.addCleanup(os.close, self.files.fd)

    def test_upload_download_replace_and_preserve_permissions(self):
        self.files.upload('árvíz.txt', io.BytesIO('első'.encode()), len('első'.encode()))
        (self.root / 'árvíz.txt').chmod(0o640)
        with self.assertRaises(FileExistsError):
            self.files.upload('árvíz.txt', io.BytesIO(b'bad'), 3)
        self.files.upload('árvíz.txt', io.BytesIO(b'next'), 4, replace=True)
        fd = self.files.open_file('árvíz.txt')
        with os.fdopen(fd, 'rb') as source:
            self.assertEqual(source.read(), b'next')
        self.assertEqual((self.root / 'árvíz.txt').stat().st_mode & 0o777, 0o640)
        self.assertFalse(list(self.root.glob('.ninja-upload-*')))

    def test_partial_upload_keeps_original_and_cleans_temporary_file(self):
        (self.root / 'existing').write_bytes(b'original')
        with self.assertRaises(ValueError):
            self.files.upload('existing', io.BytesIO(b'short'), 100, replace=True)
        self.assertEqual((self.root / 'existing').read_bytes(), b'original')
        self.assertEqual([p.name for p in self.root.iterdir()], ['existing'])

    def test_mkdir_rename_no_overwrite_and_empty_directory_delete(self):
        self.files.mkdir('folder')
        (self.root / 'folder/a').touch()
        with self.assertRaises(OSError):
            self.files.delete('folder')
        (self.root / 'b').touch()
        with self.assertRaises(ValueError):
            self.files.rename('folder/a', '../b')
        # Invalid name is rejected before renameat2.

    def test_rename_is_atomic_and_never_overwrites(self):
        (self.root / 'a').write_text('first')
        (self.root / 'b').write_text('second')
        with self.assertRaises(FileExistsError):
            self.files.rename('a', 'b')
        self.files.rename('a', 'c')
        self.assertEqual((self.root / 'c').read_text(), 'first')
        self.files.mkdir('directory')
        self.files.rename('directory', 'renamed')
        self.files.delete('renamed')
        self.assertFalse((self.root / 'renamed').exists())

    def test_paths_symlinks_special_files_and_root_are_not_followed(self):
        (self.root / 'escape').symlink_to('/etc')
        (self.root / 'secret').symlink_to('/etc/passwd')
        os.mkfifo(self.root / 'fifo')
        for path in ('../etc', '/etc', 'x/../y', 'x//y', 'bad\0name'):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                self.files.directory(path)
        for path in ('escape/passwd', 'secret', 'fifo'):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                self.files.open_file(path)
        with self.assertRaises(ValueError):
            self.files.delete('')
        with self.assertRaises(ValueError):
            self.files.delete('secret')
        with self.assertRaises((ValueError, OSError)):
            self.files.upload('secret', io.BytesIO(b'bad'), 3, replace=True)

    def test_settings_require_explicit_enable_and_per_device_token(self):
        path = self.root / 'settings.json'
        base = dict(enabled=True, token=TOKEN)
        path.write_text(json.dumps(base))
        self.assertEqual(explorer.settings(path)['idle_timeout'], 30)
        for changes in (dict(enabled=False), dict(token=''), dict(port=True),
                        dict(port=22), dict(idle_timeout=1), dict(root='/'), dict(token='a' * 23)):
            path.write_text(json.dumps(base | changes))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                explorer.settings(path)

    def test_inetd_configuration_uses_wait_and_housekeeping_cpus(self):
        with patch.object(explorer, 'STATE', self.root / 'run'):
            explorer.configure(dict(port=8080))
        conf = (self.root / 'run/inetd.conf').read_text()
        self.assertIn('8080 stream tcp wait root', conf)
        self.assertIn('taskset -c 0,1', conf)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(8)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=explorer.serve, args=(self.listener,
            dict(token=TOKEN, idle_timeout=0.35), self.root, ASSETS, 0.2), daemon=True)
        self.thread.start()
        self.addCleanup(self.finish)

    def finish(self):
        self.thread.join(timeout=1)
        self.listener.close()

    def request(self, method, url, body=None, auth=True, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        final = dict(headers or {})
        if auth:
            final['Authorization'] = 'Bearer ' + TOKEN
        connection.request(method, url, body=body, headers=final)
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def test_static_ui_is_public_but_api_requires_token(self):
        code, headers, body = self.request('GET', '/', auth=False)
        self.assertEqual(code, 200)
        self.assertIn(b'ninjaLinux', body)
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        self.assertEqual(self.request('GET', '/api/list', auth=False)[0], 401)
        self.assertEqual(self.request('GET', '/api/list', headers={'Authorization': 'Bearer wrong'}, auth=False)[0], 401)
        self.assertEqual(self.request('GET', '/api/list')[0], 200)

    def test_real_http_file_operations_and_filename_injection(self):
        name = '<img src=x onerror=alert(1)>.txt'
        from urllib.parse import quote
        path = quote(name, safe='')
        self.assertEqual(self.request('PUT', '/api/file?path=' + path, b'hello')[0], 200)
        code, _, body = self.request('GET', '/api/list')
        self.assertEqual(json.loads(body)['entries'][0]['name'], name)
        code, headers, body = self.request('GET', '/api/file?path=' + path)
        self.assertEqual(body, b'hello')
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        self.assertEqual(self.request('PUT', '/api/file?path=' + path, b'bad')[0], 409)
        self.assertEqual(self.request('POST', '/api/rename', json.dumps(dict(path=name, name='renamed')))[0], 200)
        self.assertEqual(self.request('POST', '/api/delete', json.dumps(dict(path='renamed')))[0], 200)
        self.assertFalse(list(self.root.iterdir()))

    def test_rejects_path_escape_and_malformed_requests(self):
        for url in ('/api/list?path=..', '/api/file?path=%2Fetc%2Fpasswd'):
            self.assertEqual(self.request('GET', url)[0], 400)
        self.assertEqual(self.request('POST', '/api/mkdir', '{bad')[0], 400)
        self.assertEqual(self.request('PUT', '/api/file?path=a', b'', headers={'Content-Length': str(65 * 1024 * 1024)})[0], 400)

    def test_idle_worker_exits_and_the_same_listener_can_reactivate(self):
        self.assertEqual(self.request('GET', '/api/list')[0], 200)
        self.thread.join(timeout=1)
        self.assertFalse(self.thread.is_alive())
        # inetd retains this socket and starts another worker on new activity.
        self.thread = threading.Thread(target=explorer.serve, args=(self.listener,
            dict(token=TOKEN, idle_timeout=0.35), self.root, ASSETS, 0.2), daemon=True)
        self.thread.start()
        self.assertEqual(self.request('GET', '/api/list')[0], 200)

    def test_invalid_config_consumes_queued_inetd_connection(self):
        import subprocess
        import sys
        bad = self.root / 'disabled.json'
        bad.write_text('{"enabled":false}')
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(2)
        try:
            with socket.create_connection(listener.getsockname(), timeout=1) as client:
                process = subprocess.Popen([sys.executable, str(Path(explorer.__file__)),
                    'serve', '--config', str(bad)], stdin=listener,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.assertIn(b'503 Service Unavailable', client.recv(4096))
                self.assertEqual(process.wait(timeout=1), 0)
        finally:
            listener.close()

    def test_client_without_request_times_out_and_worker_still_serves(self):
        with socket.create_connection(('127.0.0.1', self.port), timeout=1) as client:
            time.sleep(0.25)
            self.assertEqual(client.recv(1), b'')
        self.assertEqual(self.request('GET', '/api/list')[0], 200)


if __name__ == '__main__':
    unittest.main()
