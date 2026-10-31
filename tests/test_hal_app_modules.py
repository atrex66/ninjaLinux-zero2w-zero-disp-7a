"""Native module resolution and runner option checks; never runs HAL on host IPC."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'components/automation-hal/tools'
with patch.dict(os.environ, AHAL_PREFIX='/opt/automation-hal'), patch.object(sys,'path',[str(TOOLS),*sys.path]):
    spec=importlib.util.spec_from_file_location('hal_runner',TOOLS/'runner.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def test_paths_are_explicit_absolute_existing_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);(path/'alias').symlink_to(path,target_is_directory=True)
            self.assertEqual(runner.module_directories([path,path/'alias']),[str(path)])
            for bad in ('relative',path/'missing'):
                with self.assertRaises((ValueError,OSError)):runner.module_directories([bad])
            (path/'file').touch()
            with self.assertRaises(ValueError):runner.module_directories([path/'file'])
            (path/'colon:dir').mkdir()
            with self.assertRaises(ValueError):runner.module_directories([path/'colon:dir'])

@unittest.skipUnless(shutil.which('g++'),'Native resolver test requires g++')
class ResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.work.cleanup)
        root=Path(cls.work.name);cls.binary=root/'resolve';source=root/'resolve.cc'
        source.write_text('#include "module_path.hh"\n#include <iostream>\nint main(int c,char**v){std::string p,e;bool ok=ahal_module_path(v[1],v[2],v[3],p,e);std::cout<<(ok?p:e);return ok?0:1;}\n')
        subprocess.run(['g++','-std=c++17','-I'+str(ROOT/'components/automation-hal/runtime'),str(source),'-o',str(cls.binary)],check=True,capture_output=True)

    def setUp(self):
        self.workdir=tempfile.TemporaryDirectory();self.addCleanup(self.workdir.cleanup)
        root=Path(self.workdir.name);self.system=root/'system';self.app=root/'app'
        self.system.mkdir();self.app.mkdir()

    def resolve(self,name,paths=None):
        return subprocess.run([str(self.binary),name,str(self.system),str(self.app) if paths is None else paths],capture_output=True,text=True,check=False)

    def test_system_module_wins(self):
        (self.system/'threads.so').touch();(self.app/'threads.so').touch()
        result=self.resolve('threads');self.assertEqual(result.returncode,0)
        self.assertEqual(result.stdout,str(self.system/'threads.so'))

    def test_custom_module_and_ordered_multiple_directories(self):
        (self.app/'custom.so').touch()
        result=self.resolve('custom',str(self.system)+':'+str(self.app))
        self.assertEqual(result.returncode,0);self.assertEqual(result.stdout,str(self.app/'custom.so'))

    def test_missing_core_never_comes_from_app(self):
        (self.app/'hal_lib.so').touch()
        result=self.resolve('hal_lib');self.assertNotEqual(result.returncode,0)
        self.assertIn('system',result.stdout)

    def test_symlink_and_special_module_are_rejected(self):
        (self.app/'custom.so').symlink_to('/etc/passwd')
        self.assertNotEqual(self.resolve('custom').returncode,0)
        (self.app/'custom.so').unlink();os.mkfifo(self.app/'custom.so')
        self.assertNotEqual(self.resolve('custom').returncode,0)

    def test_missing_and_path_names_fail(self):
        for name in ('missing','../escape','/absolute','bad..name',''):
            self.assertNotEqual(self.resolve(name).returncode,0)
        self.assertNotEqual(self.resolve('custom','relative').returncode,0)

if __name__=='__main__':unittest.main()
