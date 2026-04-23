from __future__ import annotations

import getpass
import sys

from .providers.openrouter import delete_api_key, get_api_key, set_api_key


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in ("--delete", "-d"):
        delete_api_key()
        print("OpenRouter key removed from Credential Manager.")
        return 0
    if args and args[0] in ("--show", "-s"):
        existing = get_api_key()
        print("Key is set." if existing else "Key is not set.")
        return 0

    existing = get_api_key()
    if existing:
        print("A key is already saved. Enter a new one to replace it (Enter to cancel).")
    else:
        print("Enter your OpenRouter API key (get one at https://openrouter.ai/keys).")
    try:
        key = getpass.getpass("API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    if not key:
        print("Cancelled.")
        return 1

    try:
        set_api_key(key)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    print("Key saved to Windows Credential Manager (service=synapse).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
