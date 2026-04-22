from __future__ import annotations

import getpass
import sys

from .providers.openrouter import delete_api_key, get_api_key, set_api_key


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in ("--delete", "-d"):
        delete_api_key()
        print("Ключ OpenRouter удалён из Credential Manager.")
        return 0
    if args and args[0] in ("--show", "-s"):
        existing = get_api_key()
        print("Ключ установлен." if existing else "Ключ не задан.")
        return 0

    existing = get_api_key()
    if existing:
        print("Сейчас ключ уже сохранён. Введите новый, чтобы заменить (Enter — отмена).")
    else:
        print("Введите API-ключ OpenRouter (получить: https://openrouter.ai/keys).")
    try:
        key = getpass.getpass("API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    if not key:
        print("Отмена.")
        return 1

    try:
        set_api_key(key)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2
    print("Ключ сохранён в Windows Credential Manager (service=synapse).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
