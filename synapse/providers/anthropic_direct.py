from __future__ import annotations

from typing import Iterator

from ..i18n import t
from .base import (
    TranslationError,
    build_system_prompt,
    build_user_message,
    stream_postprocess,
)
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
            raise TranslationError(t("err.anthropic_pkg_missing", e=e))

        if self._client is None or self._client_key != api_key:
            self._client = Anthropic(api_key=api_key)
            self._client_key = api_key
        return self._client

    def translate_stream(self, text: str, src: str, dst: str) -> Iterator[str]:
        api_key = get_anthropic_key()
        if not api_key:
            raise TranslationError(
                t("err.key_missing_anthropic"),
                kind="auth",
            )
        if not api_key.isascii():
            raise TranslationError(
                t("err.key_non_ascii_anthropic"),
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
            raise TranslationError(t("err.anthropic_pkg_missing_short", e=e))

        client = self._get_client(api_key)
        system_prompt = build_system_prompt(src, dst, extra=self.custom_prompt)
        wrapped_user = build_user_message(text)

        def _raw() -> Iterator[str]:
            with client.messages.stream(
                model=self.model,
                max_tokens=4096,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": wrapped_user}],
            ) as stream:
                for delta in stream.text_stream:
                    if delta:
                        yield delta

        try:
            yield from stream_postprocess(_raw(), source_len=len(text))
        except AuthenticationError as e:
            raise TranslationError(
                t("err.invalid_key_anthropic"),
                kind="auth",
            ) from e
        except RateLimitError as e:
            raise TranslationError(t("err.rate_limit_anthropic")) from e
        except APIConnectionError as e:
            raise TranslationError(t("err.no_connection_anthropic")) from e
        except APIStatusError as e:
            status = getattr(e, "status_code", None)
            if status == 401:
                raise TranslationError(
                    t("err.invalid_key_anthropic"),
                    kind="auth",
                ) from e
            raise TranslationError(t("err.api_anthropic", status=status)) from e
        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(t("err.translation_generic", e=e)) from e
