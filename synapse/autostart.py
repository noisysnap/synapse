from __future__ import annotations

import sys
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None  # не Windows — автозапуск недоступен

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Synapse"


def _pythonw_executable() -> str:
    """Возвращает pythonw.exe рядом с текущим python.exe, если он есть.
    pythonw запускает без консольного окна — нужный режим для tray-приложения."""
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    if candidate.is_file():
        return str(candidate)
    return str(exe)


def _autostart_command() -> str:
    """Команда, которую Windows выполнит при входе в систему."""
    if getattr(sys, "frozen", False):
        # PyInstaller-сборка: sys.executable — это сам Synapse.exe.
        return f'"{Path(sys.executable).resolve()}"'
    exe = _pythonw_executable()
    # Рабочий каталог проекта (родитель пакета synapse).
    project_dir = Path(__file__).resolve().parent.parent
    # Кавычки вокруг путей с пробелами; /d нужен для cmd-обёртки.
    # Используем cmd /c cd /d "<dir>" && "<pythonw>" -m synapse, чтобы
    # модуль -m находился относительно правильного рабочего каталога.
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
    """Если автозапуск включён, но путь устарел (exe переехал) — перезаписать.
    Вызывается при старте приложения, чтобы перенос папки чинился автоматически."""
    current = _registered_command()
    if not current:
        return
    expected = _autostart_command()
    if current == expected:
        return
    try:
        enable()
    except OSError:
        # Нет прав / реестр недоступен — молча, не ломаем запуск.
        pass
