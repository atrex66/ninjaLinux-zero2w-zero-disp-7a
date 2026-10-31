# Developing ninjaLinux Qt widgets

Scope: this directory and its descendants. Original toolkit code is MIT.
Read README.md (or README.hu.md), profile.json and the existing widget source
before changing the toolkit. This is Qt Widgets / PySide6, not QML or Qt Design
Studio. Keep EsztergaDRO-specific source and machine configuration out of this
public toolkit.

## Target contract

- Target: Raspberry Pi Zero 2 W, Zero-DISP-7A, 1024×600 logical pixels,
  PySide6/Qt 6.11.2, EGLFS/KMS. Check the actual target build recipe under
  ../package/python-pyside6/ before changing the profile.
- Runtime modules are Core, Gui, Widgets, Network, OpenGL and OpenGLWidgets.
  QtDesigner, QtUiTools and QtTest belong only on the development PC/tests.
  Do not add QtQuick, SVG, WebEngine, SQL or multimedia dependencies implicitly.
- Prefer layouts, clear contrast, large text and touch targets at least 64 px
  high in the supplied templates. Leave spacing between adjacent actions.
- Use one top-level widget; keep custom OpenGL content inside that window.
  A second independent GL window is not part of this profile.
- Do not change the OS image, kernel, startup service or running Pi to test
  a widget. PC/offscreen validation comes first; report hardware limits honestly.

## Adding a custom widget

1. Implement a QWidget subclass in ninjaui/widgets.py (or a sibling module).
   Constructors must accept parent=None and work inside Designer without a
   QApplication of their own, network, HAL, files on /data, or real hardware.
2. Expose editable settings as PySide6.QtCore.Property, with plain serializable
   types and conventional setters (setValue, setHalPin, etc.). Use Signals for
   user actions and Slots for useful callable inputs. Validate values and keep
   missing/stale data visibly distinct from a valid zero or false reading.
3. Register it in designer/register_ninjaui.py using
   QPyDesignerCustomWidgetCollection.registerCustomWidget, group='ninjaLinux',
   the correct Python module, and container=False unless it is a real container.
4. Add its class/base mapping to profile.json. If it is in a new Python module,
   update the checker and generated-import allowlist intentionally; keep the
   allowlist explicit. Never allow arbitrary custom imports to silence a failure.
5. Add a .ui customwidget declaration with matching class, extends and header.
   For the current widgets, header is ninjaui.widgets. In handwritten .ui files,
   use stdset="0" for custom properties so uic calls setProperty consistently.
6. Demonstrate the widget in a suitable template or a small example without
   embedding machine-specific logic. Preserve the blank 1024×600 template.
7. Document the properties, signals, side effects and any special platform needs
   in both READMEs. Refresh the screenshot when the default appearance changes.

VFD-specific additions belong in ninjaui/vfd.py and are re-exported through
ninjaui.widgets to preserve the same Designer header. Keep the independent
point/comma behavior, finite-value validation, visible numeric overflow and
paint-cache invalidation covered by tests. Glow must stay cached, include
point/comma emission and vanish at zero brightness; test high-DPI rendering
when changing its compositing or scaling. Preserve VFD-ORIGIN.md attribution;
do not claim the approximation is the original Hunor character ROM.

## HAL boundary

- Widget imports/constructors must never import hal or connect to a machine.
- Current hal_reader.py is explicitly opt-in and read-only. Preserve that
  behavior: no component creation, setp, output writes, runtime startup or cleanup.
- Use synthetic/injected data in tests. Never attach tests to the host's or Pi's
  LinuxCNC/HAL shared memory. Missing data must not appear as a real zero.
- Polling a GUI is observational; do not implement realtime logic in Qt timers.
- TouchButton.longPressed is a one-second hold signal. Standard clicked still
  fires on release; do not accidentally connect both to conflicting actions.

## Verification and delivery

From ui-tools with a complete PC-side PySide6 installed:

```sh
python -m unittest discover -s tests
python ninjaui_tools.py check templates/panel-1024x600.ui
python ninjaui_tools.py preview templates/panel-1024x600.ui --offscreen --screenshot work/panel.png --quit-after 400
```

Create work/ before the screenshot command. Add focused tests for changed
behavior: Designer registration/property roundtrip, generated UI execution,
resources independent of source paths, malformed profiles, touch/hold semantics,
and stale input handling as applicable. Inspect the rendered 1024×600 image for
clipping and readable controls. Test on target only when explicitly within the
user's authorized deployment scope. State PC version/backend separately from
physical EGLFS evidence. Do not commit venvs, generated bundles, work files,
credentials or private machine data. Update changes.log at the repository root.
