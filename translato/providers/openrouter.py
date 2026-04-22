from __future__ import annotations

import os
import sys
from typing import Iterator

from .base import TranslationError, build_system_prompt
from .keys import (
    get_openrouter_key,
    set_openrouter_key,
    delete_openrouter_key,
)


def _dbg(*a) -> None:
    if os.environ.get("TRANSLATO_DEBUG") == "1":
        print("[translato/openrouter]", *a, file=sys.stderr, flush=True)

# Совместимость со старым импортом из setup_key.py и tray.py.
get_api_key = get_openrouter_key
set_api_key = set_openrouter_key
delete_api_key = delete_openrouter_key


class OpenRouterTranslator:
    def __init__(self, model: str, base_url: str) -> None:
        self.model = model
        self.base_url = base_url
        self._client = None
        self._client_key: str | None = None

    def _get_client(self, api_key: str):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise TranslationError(f"Пакет openai не установлен: {e}")

        if self._client is None or self._client_key != api_key:
            self._client = OpenAI(api_key=api_key, base_url=self.base_url)
            self._client_key = api_key
        return self._client

    def translate_stream(self, text: str, src: str, dst: str) -> Iterator[str]:
        api_key = get_openrouter_key()
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
            from openai import (
                APIConnectionError,
                APIStatusError,
                AuthenticationError,
                RateLimitError,
            )
        except ImportError as e:
            raise TranslationError(f"Пакет openai не установлен: {e}")

        client = self._get_client(api_key)
        system_prompt = build_system_prompt(src, dst)
        _dbg(f"→ OpenRouter | model={self.model} | key=…{api_key[-4:]} | {src}->{dst}")

        try:
            stream = client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta.content
                except (AttributeError, IndexError, TypeError):
                    continue
                if delta:
                    yield delta
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
        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(f"Сбой перевода: {e}") from e
