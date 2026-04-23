from __future__ import annotations

from threading import Lock
from typing import Iterator

from ..i18n import t
from .base import (
    TranslationError,
    build_system_prompt,
    build_user_message,
    stream_postprocess,
)
from .keys import (
    get_openrouter_key,
    set_openrouter_key,
    delete_openrouter_key,
)

# Backwards-compatible aliases for older imports in setup_key.py and tray.py.
get_api_key = get_openrouter_key
set_api_key = set_openrouter_key
delete_api_key = delete_openrouter_key


class OpenRouterTranslator:
    def __init__(self, model: str, base_url: str, custom_prompt: str = "") -> None:
        self.model = model
        self.base_url = base_url
        self.custom_prompt = custom_prompt
        self._client = None
        self._client_key: str | None = None
        self._active_stream = None
        self._active_stream_lock = Lock()

    def cancel_active_stream(self) -> None:
        """Close the active HTTP stream, if any.
        Called from the UI thread when a new translation trigger arrives —
        the old request must be aborted so it does not burn tokens or hog
        a thread-pool slot."""
        with self._active_stream_lock:
            stream = self._active_stream
            self._active_stream = None
        if stream is None:
            return
        try:
            stream.close()
        except Exception:
            pass

    def _get_client(self, api_key: str):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise TranslationError(t("err.openai_pkg_missing", e=e))

        if self._client is None or self._client_key != api_key:
            self._close_client()
            self._client = OpenAI(api_key=api_key, base_url=self.base_url)
            self._client_key = api_key
        return self._client

    def _close_client(self) -> None:
        """Close the current client's httpx pool. Without this, swapping
        the key or URL leaves the old OpenAI client around with open
        keep-alive connections until GC."""
        client = self._client
        if client is None:
            return
        self._client = None
        self._client_key = None
        try:
            client.close()
        except Exception:
            pass

    def close(self) -> None:
        """Explicit resource release. Called from app on model/URL change."""
        self._close_client()

    def translate_stream(self, text: str, src: str, dst: str) -> Iterator[str]:
        api_key = get_openrouter_key()
        if not api_key:
            raise TranslationError(
                t("err.key_missing_openrouter"),
                kind="auth",
            )
        if not api_key.isascii():
            raise TranslationError(
                t("err.key_non_ascii_openrouter"),
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
            raise TranslationError(t("err.openai_pkg_missing", e=e))

        client = self._get_client(api_key)
        system_prompt = build_system_prompt(src, dst, extra=self.custom_prompt)
        wrapped_user = build_user_message(text)

        def _raw() -> Iterator[str]:
            stream = client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": wrapped_user},
                ],
            )
            with self._active_stream_lock:
                self._active_stream = stream
            try:
                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta.content
                    except (AttributeError, IndexError, TypeError):
                        continue
                    if delta:
                        yield delta
            finally:
                # Close the connection regardless of how we exited the loop:
                # normally, through an exception, or via cancel_active_stream()
                # from another thread.
                with self._active_stream_lock:
                    if self._active_stream is stream:
                        self._active_stream = None
                try:
                    stream.close()
                except Exception:
                    pass

        try:
            yield from stream_postprocess(_raw(), source_len=len(text))
        except AuthenticationError as e:
            raise TranslationError(
                t("err.invalid_key_openrouter"),
                kind="auth",
            ) from e
        except RateLimitError as e:
            raise TranslationError(t("err.rate_limit_openrouter")) from e
        except APIConnectionError as e:
            raise TranslationError(t("err.no_connection_openrouter")) from e
        except APIStatusError as e:
            status = getattr(e, "status_code", None)
            if status == 401:
                raise TranslationError(
                    t("err.invalid_key_openrouter"),
                    kind="auth",
                ) from e
            raise TranslationError(t("err.api_generic", status=status)) from e
        except TranslationError:
            raise
        except Exception as e:
            raise TranslationError(t("err.translation_generic", e=e)) from e
