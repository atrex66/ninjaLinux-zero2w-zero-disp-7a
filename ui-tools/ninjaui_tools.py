#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""PC-side Designer, validation and deployment bundle tools."""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from ninjaui.profile import ROOT, PROFILE, check


def qt_tool(name, arguments):
    return subprocess.run([sys.executable, '-c',
        f'from PySide6.scripts.pyside_tool import {name}; {name}()', *map(str, arguments)], check=True)


def build(form, output):
    form, output = Path(form).resolve(), Path(output).resolve()
    tree, resources = check(form)
    import PySide6
    host = tuple(map(int, PySide6.__version__.split('.')[:3]))
    target = tuple(map(int, PROFILE['target_pyside'].split('.')[:3]))
    if host > target:
        raise ValueError(f'Build with PySide6 <= {PROFILE["target_pyside"]}; found {PySide6.__version__}')
    if output.exists():
        raise ValueError('Output already exists; choose a new bundle directory')
    if output == form.parent or output in form.parents or output.is_relative_to(ROOT / 'ninjaui'):
        raise ValueError('Choose an output directory separate from the source')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ninjaui-') as tmp:
        stage = Path(tmp)
        qt_tool('uic', [form, '-o', stage / 'compiled_ui.py'])
        resource_modules = {qrc.stem+'_rc' for qrc in resources}
        for qrc in resources:
            qt_tool('rcc', [qrc, '-o', stage / (qrc.stem+'_rc.py')])
        for node in ast.walk(ast.parse((stage/'compiled_ui.py').read_text())):
            if isinstance(node, ast.ImportFrom):
                allowed = {'PySide6.'+m for m in PROFILE['modules']} | {'ninjaui.widgets'}
                if node.module not in allowed:
                    raise ValueError(f'Generated import unsupported: {node.module}')
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in resource_modules:
                        raise ValueError(f'Generated resource import unsupported: {alias.name}')
        # Only target-side files: no QtDesigner/UiTools module, compiler or HAL source.
        shutil.copytree(ROOT/'ninjaui', stage/'ninjaui', ignore=shutil.ignore_patterns('__pycache__', 'profile.py'))
        (stage/'app.py').write_text('# SPDX-License-Identifier: MIT\nfrom ninjaui.runtime import main\nraise SystemExit(main())\n')
        (stage/'manifest.json').write_text(json.dumps({
            'form_class': 'Ui_'+tree.findtext('class'),
            'window_class': tree.find('widget').get('class'),
            'screen': PROFILE['screen'], 'target_pyside': PROFILE['target_pyside'],
            'built_with_pyside': PySide6.__version__, 'mode': 'offline by default'
        }, indent=2)+'\n')
        shutil.copyfile(form, stage/'source.ui')
        shutil.copyfile(ROOT/'run-pi.sh', stage/'run-pi.sh')
        (stage/'run-pi.sh').chmod(0o755)
        shutil.copyfile(ROOT.parent/'LICENSE', stage/'LICENSE')
        shutil.copytree(stage, output)
    print(f'Bundle: {output}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    new = commands.add_parser('new', help='Create a form to edit; never overwrite an existing file')
    new.add_argument('form', type=Path)
    templates = new.add_mutually_exclusive_group()
    templates.add_argument('--blank', action='store_true')
    templates.add_argument('--vfd', action='store_true', help='Use the Hunor-style VFD showcase')
    edit = commands.add_parser('designer', help='Open the PySide6 Designer with ninjaLinux widgets')
    edit.add_argument('form', type=Path)
    validate = commands.add_parser('check', help='Validate a .ui without importing Qt')
    validate.add_argument('form', type=Path)
    package = commands.add_parser('build', help='Compile .ui/.qrc on the PC into a portable Python app')
    package.add_argument('form', type=Path)
    package.add_argument('--output', type=Path, required=True)
    preview = commands.add_parser('preview', help='Compile to a temporary directory and run on the PC')
    preview.add_argument('form', type=Path)
    preview.add_argument('--demo', action='store_true')
    preview.add_argument('--offscreen', action='store_true')
    preview.add_argument('--screenshot', type=Path)
    preview.add_argument('--quit-after', type=int, default=0, metavar='MS')
    args = p.parse_args()
    try:
        if args.command == 'new':
            name = 'vfd-1024x600.ui' if args.vfd else ('blank-1024x600.ui' if args.blank else 'panel-1024x600.ui')
            template = ROOT/'templates'/name
            args.form.parent.mkdir(parents=True, exist_ok=True)
            with args.form.open('xb') as out:
                out.write(template.read_bytes())
            print(args.form)
        elif args.command == 'check':
            check(args.form)
            print('PASS: ninjaLinux 1024x600 form profile')
        elif args.command == 'designer':
            from PySide6 import QtDesigner  # Fail early if the PC package is incomplete.
            env = os.environ.copy()
            env['PYSIDE_DESIGNER_PLUGINS'] = str(ROOT/'designer')
            env['PYTHONPATH'] = str(ROOT)+os.pathsep+env.get('PYTHONPATH', '')
            return subprocess.call([sys.executable, '-c',
                'from PySide6.scripts.pyside_tool import designer; designer()', str(args.form.resolve())], env=env)
        elif args.command == 'build':
            build(args.form, args.output)
        else:
            with tempfile.TemporaryDirectory(prefix='ninjaui-preview-') as tmp:
                bundle = Path(tmp)/'app'
                build(args.form, bundle)
                command = [sys.executable, str(bundle/'app.py'), '--quit-after', str(args.quit_after)]
                if args.demo:
                    command.append('--demo')
                if args.screenshot:
                    command.extend(['--screenshot', str(args.screenshot.resolve())])
                env = os.environ.copy()
                if args.offscreen:
                    env['QT_QPA_PLATFORM'] = 'offscreen'
                return subprocess.call(command, env=env)
    except (OSError, ValueError, ImportError, subprocess.CalledProcessError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
