from __future__ import annotations

import keyring

KEYRING_SERVICE = "translato"
KEY_OPENROUTER = "openrouter_api_key"
KEY_ANTHROPIC = "anthropic_api_key"


def _get(user: str) -> str | None:
    try:
        return keyring.get_password(KEYRING_SERVICE, user)
    except keyring.errors.KeyringError:
        return None


def _set(user: str, key: str) -> None:
    key = key.strip()
    if not key.isascii():
        bad = [(i, hex(ord(c))) for i, c in enumerate(key) if ord(c) > 127]
        raise ValueError(
            f"Ключ содержит не-ASCII символы в позициях {bad}. "
            "Скорее всего при вставке попала буква в другой кодировке. "
            "Скопируйте ключ заново с сайта провайдера."
        )
    keyring.set_password(KEYRING_SERVICE, user, key)


def _delete(user: str) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, user)
    except keyring.errors.PasswordDeleteError:
        pass


def get_openrouter_key() -> str | None:
    return _get(KEY_OPENROUTER)


def set_openrouter_key(key: str) -> None:
    _set(KEY_OPENROUTER, key)


def delete_openrouter_key() -> None:
    _delete(KEY_OPENROUTER)


def get_anthropic_key() -> str | None:
    return _get(KEY_ANTHROPIC)


def set_anthropic_key(key: str) -> None:
    _set(KEY_ANTHROPIC, key)


def delete_anthropic_key() -> None:
    _delete(KEY_ANTHROPIC)
