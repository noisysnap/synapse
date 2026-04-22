"""Точка входа для PyInstaller-сборки.
PyInstaller импортирует этот файл как top-level script, поэтому здесь нужен
абсолютный импорт — относительный `.app` отсюда не работает.
Для dev-режима по-прежнему используется `python -m synapse` → __main__.py."""
from synapse.app import main

if __name__ == "__main__":
    raise SystemExit(main())
