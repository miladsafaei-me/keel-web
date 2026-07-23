"""Gemini ``generateContent`` image generation: call the API, decode the inline
image, save it as WebP.

The HTTP + decode + retry core is generic. Everything project-specific — the API
key, the endpoint URL, the aspect ratio, and the system-instruction text — is
resolved through ``KEEL_WEB["image_gen"]`` hooks so the host can source them from
its own settings or a DB-backed settings model. Each resolver has a sensible
default (env-style settings) so the module works with zero hooks configured.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import requests
from django.conf import settings

from ..config import call_hook, image_gen_setting
from .image_upload import save_image_bytes_as_webp

logger = logging.getLogger(__name__)

_MAX_PROMPT_CHARS = 8000
_ALLOWED_ASPECT = frozenset({"16:9", "4:3", "1:1"})
_DEFAULT_MODEL = "gemini-2.5-flash-image"
_GENERATE_CONTENT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def _resolve_api_key() -> str:
    key = call_hook(image_gen_setting("api_key_hook"), default=None)
    if key:
        return key
    return (getattr(settings, "GEMINI_API_KEY", "") or "").strip()


def _default_generate_url() -> str:
    model = (getattr(settings, "GEMINI_IMAGE_MODEL", "") or _DEFAULT_MODEL).strip()
    return _GENERATE_CONTENT_URL.format(model=model)


def _resolve_hero_url() -> str:
    return call_hook(image_gen_setting("hero_url_hook"), default=None) or _default_generate_url()


def _resolve_inline_url() -> str:
    return call_hook(image_gen_setting("inline_url_hook"), default=None) or _default_generate_url()


def _resolve_aspect_ratio() -> str:
    ar = (call_hook(image_gen_setting("aspect_ratio_hook"), default=None) or "16:9").strip()
    return ar if ar in _ALLOWED_ASPECT else "16:9"


def _resolve_hero_system_instruction() -> str:
    return (call_hook(image_gen_setting("hero_system_instruction_hook"), default="") or "").strip()


def _resolve_inline_system_instruction() -> str:
    return (call_hook(image_gen_setting("inline_system_instruction_hook"), default="") or "").strip()


def _extract_first_image_bytes(data: dict[str, Any]) -> bytes | None:
    feedback = data.get("promptFeedback") or {}
    block = feedback.get("blockReason")
    if block:
        logger.warning("Gemini promptFeedback blockReason=%s", block)

    for cand in data.get("candidates") or []:
        content = cand.get("content") or {}
        for part in content.get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if not isinstance(inline, dict):
                continue
            b64 = inline.get("data")
            mime = (inline.get("mimeType") or inline.get("mime_type") or "").lower()
            if not b64 or "image" not in mime:
                continue
            try:
                return base64.b64decode(b64, validate=True)
            except Exception:
                logger.exception("Failed to decode inline image payload")
                return None
    return None


def _gemini_image_request(url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    connect_timeout = float(getattr(settings, "GEMINI_HTTP_CONNECT_TIMEOUT", 45.0))
    read_timeout = float(getattr(settings, "GEMINI_HTTP_READ_TIMEOUT", 300.0))
    retries = max(1, int(getattr(settings, "GEMINI_HTTP_RETRIES", 4)))
    timeout = (connect_timeout, read_timeout)

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
        "User-Agent": "KeelWebImageGen/1.0",
    }

    last_error: BaseException | None = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                delay = min(20.0, 2.0 * (2**attempt))
                logger.warning(
                    "Gemini image HTTP %s attempt %s/%s; retry in %.1fs",
                    resp.status_code,
                    attempt + 1,
                    retries,
                    delay,
                )
                time.sleep(delay)
                continue
            if not resp.ok:
                try:
                    body = resp.json()
                    err = body.get("error") if isinstance(body, dict) else None
                    msg = err.get("message", resp.text) if isinstance(err, dict) else resp.text
                except Exception:
                    msg = resp.text or resp.reason
                raise RuntimeError(msg or f"HTTP {resp.status_code}") from None
            return resp.json()
        except RuntimeError:
            raise
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as exc:
            last_error = exc
            if attempt >= retries - 1:
                break
            delay = min(25.0, 1.5 * (2**attempt))
            time.sleep(delay)

    raise RuntimeError(f"Gemini image request failed after {retries} attempt(s): {last_error!r}") from last_error


def _generate(*, user_prompt: str, url: str, system_instruction: str, media_subpath: str) -> str:
    prompt = (user_prompt or "").strip()
    if not prompt:
        raise ValueError("Prompt is required.")
    if len(prompt) > _MAX_PROMPT_CHARS:
        prompt = prompt[:_MAX_PROMPT_CHARS]

    api_key = _resolve_api_key()
    if not api_key:
        raise ValueError(
            "No image API key configured. Set an image AI key via the "
            "KEEL_WEB['image_gen']['api_key_hook'] or GEMINI_API_KEY."
        )

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": _resolve_aspect_ratio()},
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    data = _gemini_image_request(url, api_key, payload)
    if isinstance(data, dict) and "error" in data:
        err = data.get("error")
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RuntimeError(msg)

    raw_image = _extract_first_image_bytes(data)
    if not raw_image:
        raise RuntimeError(
            "The model returned no image. Use a Gemini image-capable model "
            "(e.g. gemini-2.5-flash-image) or check the API error message."
        )

    return save_image_bytes_as_webp(raw_image, media_subpath=media_subpath)


def generate_featured_image_media_relative_path(*, user_prompt: str) -> str:
    """Generate a hero/featured image, persist as WebP under ``blog/featured``.

    Returns a media-relative POSIX path (same shape as ``save_upload_as_webp``).
    """
    return _generate(
        user_prompt=user_prompt,
        url=_resolve_hero_url(),
        system_instruction=_resolve_hero_system_instruction(),
        media_subpath="blog/featured",
    )


def generate_inline_image_media_relative_path(*, user_prompt: str) -> str:
    """Generate an in-body image, persist as WebP under ``blog/inline``."""
    return _generate(
        user_prompt=user_prompt,
        url=_resolve_inline_url(),
        system_instruction=_resolve_inline_system_instruction(),
        media_subpath="blog/inline",
    )
