# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Synapse — windowed onedir build.
# Build: pyinstaller Synapse.spec

from pathlib import Path

project_root = Path(SPECPATH)
icon_path = project_root / "synapse" / "assets" / "icon.ico"

# Keyring подбирает backend через entry points, а PyInstaller их не видит —
# явно подтягиваем Windows-бэкенд, иначе get/set_password упадут в рантайме.
# pynput на Windows использует win32-подмодули, которые тоже невидимы статически.
hidden_imports = [
    "keyring.backends.Windows",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
]

# В сборку кладём папку assets целиком — tray.py обращается к ней через
# Path(__file__).parent / "assets", что в frozen режиме будет внутри _internal.
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
