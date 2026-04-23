from __future__ import annotations

import sys
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None  # not Windows — autostart unavailable

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Synapse"


def _pythonw_executable() -> str:
    """Return pythonw.exe next to the current python.exe if it exists.
    pythonw runs without a console window — the right mode for a tray app."""
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    if candidate.is_file():
        return str(candidate)
    return str(exe)


def _autostart_command() -> str:
    """Command Windows will execute on user logon."""
    if getattr(sys, "frozen", False):
        # PyInstaller build: sys.executable is Synapse.exe itself.
        return f'"{Path(sys.executable).resolve()}"'
    exe = _pythonw_executable()
    # Project root (parent of the synapse package).
    project_dir = Path(__file__).resolve().parent.parent
    # Quote paths containing spaces; /d is required for the cmd wrapper.
    # We use cmd /c cd /d "<dir>" && "<pythonw>" -m synapse so that the
    # -m module resolves relative to the correct working directory.
    return f'cmd /c cd /d "{project_dir}" && "{exe}" -m synapse'


def is_supported() -> bool:
    return winreg is not None


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> None:
    if winreg is None:
        return
    cmd = _autostart_command()
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, cmd)


def disable() -> None:
    if winreg is None:
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _VALUE_NAME)
    except FileNotFoundError:
        return


def apply(enabled: bool) -> None:
    if enabled:
        enable()
    else:
        disable()


def _registered_command() -> str | None:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            return value if isinstance(value, str) else None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def self_heal() -> None:
    """If autostart is enabled but the path is stale (exe was moved), rewrite it.
    Called on app startup so moving the build folder fixes itself automatically."""
    current = _registered_command()
    if not current:
        return
    expected = _autostart_command()
    if current == expected:
        return
    try:
        enable()
    except OSError:
        # No permissions / registry inaccessible — silent, do not break startup.
        pass
