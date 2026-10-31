import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import cpu_layout
import install_cpu_layout


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'layout.json'
        self.data = dict(version=1, system_cpus=[0, 1], ui_cpu=2, hal_cpu=3)
        self.config.write_text(json.dumps(self.data))

    def test_rejects_overlaps_invalid_ids_and_schema(self):
        for change in [dict(hal_cpu=2), dict(system_cpus=[0, 0]), dict(ui_cpu=True), dict(hal_cpu=-1), dict(hal_cpu=1024), dict(version=True), dict(system_cpus=[]), dict(extra=1)]:
            self.config.write_text(json.dumps(self.data | change))
            with self.subTest(change=change),self.assertRaises(ValueError):cpu_layout.load_layout(self.config)

    def test_offline_and_failed_readback_fail_closed(self):
        with patch.object(cpu_layout, 'online_cpus', return_value={0, 1, 2}),patch.object(os, 'sched_setaffinity') as setmask:
            with self.assertRaisesRegex(ValueError,'unavailable'):cpu_layout.apply_role('hal',self.config)
            setmask.assert_not_called()
        with patch.object(cpu_layout, 'online_cpus', return_value={0, 1, 2, 3}),patch.object(os,'sched_setaffinity'),patch.object(os,'sched_getaffinity',return_value={0}):
            with self.assertRaisesRegex(RuntimeError,'pinning failed'):cpu_layout.apply_role('ui',self.config)

    def test_real_child_and_thread_affinity_and_environment(self):
        allowed=sorted(os.sched_getaffinity(0))
        if len(allowed)<3:self.skipTest('Three allowed CPUs needed for live affinity test')
        layout=dict(version=1,system_cpus=[allowed[0]],ui_cpu=allowed[1],hal_cpu=allowed[2])
        self.config.write_text(json.dumps(layout))
        code='import os,json,threading; r={"main":sorted(os.sched_getaffinity(0)),"rt":os.environ["RTAPI_CPU_NUMBER"]}; t=threading.Thread(target=lambda:r.update(thread=sorted(os.sched_getaffinity(0)))); t.start(); t.join(); print(json.dumps(r))'
        for role,cpus in [('hal',[allowed[2]]),('ui',[allowed[1]]),('system',[allowed[0]])]:
            out=subprocess.check_output([sys.executable,str(TOOLS/'cpu_layout.py'),'--config',str(self.config),'--role',role,'--',sys.executable,'-c',code],text=True)
            self.assertEqual(json.loads(out),dict(main=cpus,thread=cpus,rt=str(allowed[2])))

    def test_invalid_config_does_not_execute_command(self):
        self.data['hal_cpu']=-1;self.config.write_text(json.dumps(self.data))
        marker=self.root/'executed'
        result=subprocess.run([sys.executable,str(TOOLS/'cpu_layout.py'),'--config',str(self.config),'--role','hal','--',sys.executable,'-c',f'open({str(marker)!r},"w").close()'],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(marker.exists())

    def test_node_editor_launcher_preserves_affinity_and_arguments(self):
        allowed=sorted(os.sched_getaffinity(0))
        if len(allowed)<3:self.skipTest('Three allowed CPUs needed')
        self.config.write_text(json.dumps(dict(version=1,system_cpus=[allowed[0]],ui_cpu=allowed[1],hal_cpu=allowed[2])))
        # Replace only the final Qt application with a probe; use the real helper.
        interpreter=self.root/'python-probe'
        interpreter.write_text('#!'+sys.executable+'\nimport os,sys,json\nif sys.argv[1]=="app.py":\n print(json.dumps([sorted(os.sched_getaffinity(0)),sys.argv[2:]]))\nelse:\n os.execv(sys.executable,[sys.executable,*sys.argv[1:]])\n')
        interpreter.chmod(0o755)
        editor=TOOLS.parents[1]/'NinjaNodeEditor'
        env=os.environ | dict(PLC_PYTHON=str(interpreter),AUTOMATION_CPU_CONFIG=str(self.config),AUTOMATION_CPU_HELPER=str(TOOLS/'cpu_layout.py'))
        out=subprocess.check_output([str(editor/'run-pinned.sh'),'--windowed','--project','a file.json'],env=env,text=True)
        self.assertEqual(json.loads(out),[[allowed[1]],['--windowed','--project','a file.json']])

    def test_runner_rejects_bad_profile_before_runtime(self):
        self.data['hal_cpu']=-1;self.config.write_text(json.dumps(self.data))
        env=os.environ | dict(AHAL_PREFIX=str(self.root))
        result=subprocess.run([sys.executable,str(TOOLS/'runner.py'),'run','--cpu-config',str(self.config),'--mode','sim','absent.hal'],env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('CPU indices',result.stderr)

    def test_install_rolls_back_if_write_fails(self):
        target=self.root/'etc/existing';target.parent.mkdir();target.write_text('before')
        files={'/etc/existing':'after','/etc/new':'new'}
        real=install_cpu_layout.write_atomic
        def fail_new(path,content,mode):
            if path.name=='new':raise OSError('simulated disk error')
            real(path,content,mode)
        with patch.object(install_cpu_layout,'write_atomic',side_effect=fail_new):
            with self.assertRaises(OSError):install_cpu_layout.install(self.root,files)
        self.assertEqual(target.read_text(),'before');self.assertFalse((self.root/'etc/new').exists())

    def test_boot_update_preserves_root_and_is_idempotent(self):
        before='console=tty3 root=PARTUUID=test quiet isolcpus=1 irqaffinity=2\n'
        after=install_cpu_layout.boot_line(before,self.data)
        self.assertIn('root=PARTUUID=test',after);self.assertIn('isolcpus=domain,managed_irq,2,3',after)
        self.assertIn('irqaffinity=0,1',after);self.assertEqual(after,install_cpu_layout.boot_line(after,self.data))
        with self.assertRaises(ValueError):install_cpu_layout.boot_line('quiet\n',self.data)
        with self.assertRaises(ValueError):install_cpu_layout.boot_line('root=test\nquiet\n',self.data)

    def test_stage_install_backup_and_service_masks(self):
        boot=self.root/'boot/firmware/cmdline.txt';boot.parent.mkdir(parents=True);boot.write_text('console=tty3 root=test quiet\n')
        files=install_cpu_layout.planned_files(self.root,self.config)
        self.assertIn('AllowedCPUs=3',files['/etc/systemd/system/magorautomate-hal.service.d/90-automation-cpu.conf'])
        self.assertIn('AllowedCPUs=2',files['/etc/systemd/system/magorautomate.service.d/90-automation-cpu.conf'])
        self.assertIn('CPUAffinity=0 1',files['/etc/systemd/system.conf.d/90-automation-cpu.conf'])
        backup=install_cpu_layout.install(self.root,files)
        saved=json.loads((backup/'manifest.json').read_text())
        self.assertIsNone(saved['/etc/automation-hal/cpu-layout.json'])
        import base64
        self.assertEqual(base64.b64decode(saved['/boot/firmware/cmdline.txt']['data']),b'console=tty3 root=test quiet\n')
        self.assertEqual(cpu_layout.load_layout(self.root/'etc/automation-hal/cpu-layout.json'),self.data)
        self.assertEqual(boot.read_text(),files['/boot/firmware/cmdline.txt'])


if __name__=='__main__':unittest.main()
