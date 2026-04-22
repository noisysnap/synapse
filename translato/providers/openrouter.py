from __future__ import annotations

import keyring

from .base import TranslationError

KEYRING_SERVICE = "translato"
KEYRING_USER = "openrouter_api_key"

LANG_NAMES = {"ru": "Russian", "en": "English"}


def get_api_key() -> str | None:
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except keyring.errors.KeyringError:
        return None


def set_api_key(key: str) -> None:
    key = key.strip()
    if not key.isascii():
        bad = [(i, hex(ord(c))) for i, c in enumerate(key) if ord(c) > 127]
        raise ValueError(
            f"Ключ содержит не-ASCII символы в позициях {bad}. "
            "Скорее всего при вставке попала буква в другой кодировке. "
            "Скопируйте ключ заново со страницы openrouter.ai/keys."
        )
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)


def delete_api_key() -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass


def _build_system_prompt(src: str, dst: str) -> str:
    src_name = LANG_NAMES.get(src, src)
    dst_name = LANG_NAMES.get(dst, dst)
    return (
        f"You are a professional translator from {src_name} to {dst_name}. "
        "Output ONLY the translation, with no comments, no quotation marks, "
        "no prefixes, no explanations. Preserve the original formatting, line "
        "breaks, punctuation, proper names, URLs, code, and numbers exactly. "
        "Use natural, idiomatic phrasing in the target language."
    )


class OpenRouterTranslator:
    def __init__(self, model: str, base_url: str) -> None:
        self.model = model
        self.base_url = base_url

    def translate(self, text: str, src: str, dst: str) -> str:
        api_key = get_api_key()
        if not api_key:
            raise TranslationError(
                "API-ключ OpenRouter не задан. Откройте «Настройки» в трее.",
                kind="auth",
            )
        if not api_key.isascii():
            raise TranslationError(
                "В сохранённом ключе есть не-ASCII символы. "
                "Скопируйте ключ заново со страницы openrouter.ai/keys "
                "и вставьте его через «Настройки».",
                kind="auth",
            )

        try:
            from openai import OpenAI
            from openai import APIStatusError, AuthenticationError, RateLimitError, APIConnectionError
        except ImportError as e:
            raise TranslationError(f"Пакет openai не установлен: {e}")

        client = OpenAI(api_key=api_key, base_url=self.base_url)
        system_prompt = _build_system_prompt(src, dst)

        try:
            resp = client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
        except AuthenticationError as e:
            raise TranslationError(
                "Недействительный API-ключ. Введите ключ заново в «Настройках».",
                kind="auth",
            ) from e
        except RateLimitError as e:
            raise TranslationError("Превышен лимит запросов OpenRouter. Попробуйте позже.") from e
        except APIConnectionError as e:
            raise TranslationError("Нет соединения с OpenRouter. Проверьте интернет.") from e
        except APIStatusError as e:
            status = getattr(e, "status_code", None)
            if status == 401:
                raise TranslationError(
                    "Недействительный API-ключ. Введите ключ заново в «Настройках».",
                    kind="auth",
                ) from e
            raise TranslationError(f"Ошибка API (код {status}).") from e
        except Exception as e:
            raise TranslationError(f"Сбой перевода: {e}") from e

        try:
            content = resp.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as e:
            raise TranslationError("Пустой ответ от модели.") from e

        if not content:
            raise TranslationError("Пустой ответ от модели.")
        return content.strip()
