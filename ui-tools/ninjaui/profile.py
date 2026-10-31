# SPDX-License-Identifier: MIT
"""Conservative .ui checks for the selected ninjaLinux image, without Qt imports."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'profile.json').read_text())


def read_xml(path):
    data = path.read_bytes()
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entity declarations are not supported')
    try:
        return ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f'Invalid XML in {path.name}: {error}') from error


def local_file(base, name):
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError(f'Missing or outside project directory: {name}')
    return path


def check(path):
    """Return parsed form and its referenced qrc files, or a useful failure."""
    path = Path(path).resolve()
    root = read_xml(path)
    widget = root.find('widget')
    if root.tag != 'ui' or widget is None or widget.get('class') not in ('QWidget', 'QMainWindow'):
        raise ValueError('Use a QWidget or QMainWindow top-level form')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', root.findtext('class', '')):
        raise ValueError('The form class must be a Python identifier')
    size = widget.find("property[@name='geometry']/rect")
    if size is None or [int(size.findtext(x, '0')) for x in ('width', 'height')] != PROFILE['screen']:
        raise ValueError('Top-level geometry must be 1024 x 600')
    for key in ('minimumSize', 'maximumSize'):
        size = widget.find(f"property[@name='{key}']/size")
        if size is not None:
            values = [int(size.findtext(x, '0')) for x in ('width', 'height')]
            invalid = any(v > limit for v, limit in zip(values, PROFILE['screen'])) if key == 'minimumSize' else any(v < limit for v, limit in zip(values, PROFILE['screen']))
            if invalid:
                raise ValueError(f'{key} prevents a 1024 x 600 window')
    allowed = set(PROFILE['widgets']) | set(PROFILE['custom_widgets'])
    names = set()
    for node in root.iter():
        if node.tag == 'widget' and node.get('class') not in allowed:
            raise ValueError(f'Unsupported widget: {node.get("class")}')
        if node.tag == 'layout' and node.get('class') not in PROFILE['layouts']:
            raise ValueError(f'Unsupported layout: {node.get("class")}')
        if node.tag in ('widget', 'layout', 'action', 'spacer'):
            name = node.get('name', '')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name) or name in names:
                raise ValueError(f'Invalid or duplicate objectName: {name}')
            names.add(name)
        if node.tag == 'iconset' and node.get('theme') and not any((n.text or '').startswith(':/') for n in node):
            raise ValueError('Theme-only icons are unavailable in this image; use a PNG resource')
        if node.tag in ('pixmap', 'normaloff', 'normalon', 'disabledoff', 'disabledon', 'activeoff', 'activeon', 'selectedoff', 'selectedon'):
            if node.text and not node.text.startswith(':/'):
                raise ValueError('Images must use a .qrc resource path (:/...), not a local file')
        if node.tag == 'string':
            for url in re.findall(r'url\(\s*[\'"]?([^\'")\s]+)', node.text or '', re.I):
                if not url.startswith(':/'):
                    raise ValueError('Stylesheet images must use :/ resource paths')
    declared = {}
    for custom in root.findall('customwidgets/customwidget'):
        name = custom.findtext('class')
        if name not in PROFILE['custom_widgets'] or name in declared:
            raise ValueError(f'Unknown or duplicate custom declaration: {name}')
        bases = PROFILE.get('custom_widget_bases', {}).get(name, [PROFILE['custom_widgets'][name]])
        if custom.findtext('extends') not in bases or custom.findtext('header') != 'ninjaui.widgets':
            raise ValueError(f'{name}: use the profile base class and header ninjaui.widgets')
        declared[name] = True
    used = {n.get('class') for n in root.iter('widget')} & set(PROFILE['custom_widgets'])
    if used - declared.keys():
        raise ValueError(f'Missing custom declarations: {sorted(used - declared.keys())}')
    resources = []
    resource_modules = set()
    for item in root.findall('resources/include'):
        qrc = local_file(path.parent, item.get('location', ''))
        if qrc.suffix != '.qrc' or not qrc.stem.isidentifier():
            raise ValueError('Resource names must be Python identifiers ending in .qrc')
        if qrc.stem in resource_modules:
            raise ValueError('Resource basenames must be unique')
        resource_modules.add(qrc.stem)
        for image in read_xml(qrc).iter('file'):
            file = local_file(qrc.parent, image.text or '')
            if not file.is_relative_to(path.parent) or file.suffix.lower() != '.png':
                raise ValueError('This profile supports project-local PNG resources only')
        resources.append(qrc)
    return root, resources
