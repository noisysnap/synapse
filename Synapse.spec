# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Synapse — windowed onedir build.
# Build: pyinstaller Synapse.spec

from pathlib import Path

project_root = Path(SPECPATH)
icon_path = project_root / "synapse" / "assets" / "icon.ico"

# keyring resolves its backend through entry points which PyInstaller does not
# pick up — explicitly pull in the Windows backend, otherwise get/set_password
# will fail at runtime. pynput on Windows uses win32 submodules that are also
# invisible to static analysis.
hidden_imports = [
    "keyring.backends.Windows",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
]

# The whole assets folder is bundled — tray.py reads it via
# Path(__file__).parent / "assets", which in frozen mode lives inside _internal.
datas = [
    (str(project_root / "synapse" / "assets"), "synapse/assets"),
]

a = Analysis(
    [str(project_root / "run_synapse.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "test",
        "pydoc_data",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Synapse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_path) if icon_path.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Synapse",
)
