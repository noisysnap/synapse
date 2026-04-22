from __future__ import annotations

from typing import Iterator

from .base import TranslationError, build_system_prompt
from .keys import get_anthropic_key


class AnthropicTranslator:
    def __init__(self, model: str, custom_prompt: str = "") -> None:
        self.model = model
        self.custom_prompt = custom_prompt
        self._client = None
        self._client_key: str | None = None

    def _get_client(self, api_key: str):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise TranslationError(
                f"Пакет anthropic не установлен: {e}. Установите: pip install anthropic"
            )

        if self._client is None or self._client_key != api_key:
            self._client = Anthropic(api_key=api_key)
            self._client_key = api_key
        return self._client

    def translate_stream(self, text: str, src: str, dst: str) -> Iterator[str]:
        api_key = get_anthropic_key()
        if not api_key:
            raise TranslationError(
                "API-ключ Anthropic не задан. Откройте «Настройки» в трее.",
                kind="auth",
            )
        if not api_key.isascii():
            raise TranslationError(
                "В сохранённом ключе есть не-ASCII символы. "
                "Скопируйте ключ заново с console.anthropic.com "
                "и вставьте его через «Настройки».",
                kind="auth",
            )

        try:
            from anthropic import (
                APIConnectionError,
                APIStatusError,
                AuthenticationError,
                RateLimitError,
            )
        except ImportError as e:
            raise TranslationError(f"Пакет anthropic не установлен: {e}")

        client = self._get_client(api_key)
        system_prompt = build_system_prompt(src, dst, extra=self.custom_prompt)

        try:
            with client.messages.stream(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
            ) as stream:
                for delta in stream.text_stream:
                    if delta:
                        yield delta
        except AuthenticationError as e:
            raise TranslationError(
                "Недействительный API-ключ Anthropic. Введите ключ заново в «Настройках».",
                kind="auth",
            ) from e
        except RateLimitError as e:
            raise TranslationError("Превышен лимит запросов Anthropic. Попробуйте позже.") from e
        except APIConnectionError as e:
            raise TranslationError("Нет соединения с Anthropic. Проверьте интернет.") from e
        except APIStatusError as e:
            status = getattr(e, "status_code", None)
            if status == 401:
                raise TranslationError(
                    "Недействительный API-ключ Anthropic. Введите ключ заново в «Настройках».",
                    kind="auth",
                ) from e
            raise TranslationError(f"Ошибка API Anthropic (код {status}).") from e
        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(f"Сбой перевода: {e}") from e
