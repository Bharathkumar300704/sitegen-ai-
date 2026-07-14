"""
OpenRouter API client — uses the REST API directly via httpx.

OpenRouter exposes an OpenAI-compatible /chat/completions endpoint.
All AI calls in this project go through the two public functions:
  - generate_content(prompt, system_instruction, max_retries) -> str
  - check_api_key_status() -> dict

Configuration (loaded from .env):
  OPENROUTER_API_KEY   — required, Bearer token
  OPENROUTER_MODEL     — optional, defaults to deepseek/deepseek-chat-v3-0324:free
"""

import os
import time
import httpx
from dotenv import load_dotenv
from config.logging_config import get_logger

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_COMPLETIONS_URL = f"{OPENROUTER_BASE_URL}/chat/completions"

# Default model — change OPENROUTER_MODEL in .env to switch easily
# Confirmed working free models (as of 2026-07):
#   nvidia/nemotron-3-nano-30b-a3b:free  (30B, fast, general purpose)
#   qwen/qwen3-coder:free               (coder, 1M ctx, may be rate-limited)
#   google/gemma-4-31b-it:free          (31B, general purpose)
DEFAULT_MODEL = "nvidia/nemotron-3-nano-30b-a3b:free"

# AI Provider identifier (used in logs and config)
AI_PROVIDER = "openrouter"


# ── Key loading ───────────────────────────────────────────────────────────────
def _load_api_key() -> str:
    """Read the OpenRouter API key directly from the environment / .env file."""
    load_dotenv(override=True)
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def _get_api_key() -> str:
    key = _load_api_key()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Add it to your .env file and restart the server."
        )
    return key


def _get_model() -> str:
    """Read the model name from env, falling back to the default free model."""
    load_dotenv(override=True)
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip()


# ── Core REST caller ──────────────────────────────────────────────────────────
def _call_openrouter(prompt: str, system_instruction: str = None) -> str:
    """
    POST to OpenRouter /chat/completions.
    Returns the generated text string on success, raises RuntimeError on failure.
    Logs: request URL, model, prompt length, HTTP status, response time, response length.
    """
    api_key = _get_api_key()
    model   = _get_model()

    # Build messages array
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    body = {
        "model":    model,
        "messages": messages,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    # Masked key for logging
    key_preview = f"{api_key[:12]}...{api_key[-4:]}" if len(api_key) > 16 else "****"

    # ── PRE-REQUEST LOG ───────────────────────────────────────────────────────
    logger.info("═" * 70)
    logger.info("OPENROUTER REQUEST")
    logger.info(f"  URL          : {CHAT_COMPLETIONS_URL}")
    logger.info(f"  Model        : {model}")
    logger.info(f"  API Key      : {key_preview}")
    logger.info(f"  Prompt len   : {len(prompt)} chars")
    logger.info(f"  Prompt head  : {prompt[:300]!r}")
    if system_instruction:
        logger.info(f"  SysInstruct  : {system_instruction[:100]!r}")
    logger.info("═" * 70)

    t_start = time.monotonic()

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(CHAT_COMPLETIONS_URL, json=body, headers=headers)

        elapsed = time.monotonic() - t_start

        # ── POST-REQUEST LOG ──────────────────────────────────────────────────
        logger.info("─" * 70)
        logger.info("OPENROUTER RESPONSE")
        logger.info(f"  HTTP Status  : {response.status_code}")
        logger.info(f"  Response Time: {elapsed:.2f}s")

        raw = response.text
        logger.info(f"  Raw len      : {len(raw)} chars")
        logger.info(f"  Raw head     : {raw[:500]!r}")
        logger.info("─" * 70)

        if response.status_code != 200:
            _handle_http_error(response.status_code, raw)

        data = response.json()
        logger.info(f"  Parsed JSON keys: {list(data.keys())}")

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as parse_err:
            logger.error(f"Unexpected response structure: {data}")
            raise RuntimeError(
                f"OpenRouter response parsing failed: {parse_err}\n"
                f"Full response: {raw[:1000]}"
            )

        logger.info(f"  Extracted text len : {len(text)}")
        logger.info(f"  Text head          : {text[:300]!r}")
        return text

    except httpx.TimeoutException as e:
        logger.error(f"OpenRouter request TIMED OUT after 120s: {e}")
        raise RuntimeError(f"OpenRouter request timed out: {e}")

    except httpx.RequestError as e:
        logger.error(f"OpenRouter network error: {type(e).__name__}: {e}")
        raise RuntimeError(f"OpenRouter network error: {e}")


# ── HTTP error handler ────────────────────────────────────────────────────────
def _handle_http_error(status: int, raw: str):
    """Parse and raise a human-readable error from a non-200 HTTP response."""
    import json as _json
    try:
        err_data = _json.loads(raw)
        msg = (
            err_data.get("error", {}).get("message", "")
            or err_data.get("message", raw[:500])
        )
        code = err_data.get("error", {}).get("code", status)
    except Exception:
        msg  = raw[:500]
        code = status

    full_msg = f"[HTTP {code}]: {msg}"
    logger.error(f"OpenRouter API error: {full_msg}")

    if status == 400:
        raise RuntimeError(f"BAD_REQUEST: {full_msg}")
    elif status == 401:
        raise RuntimeError(
            f"UNAUTHORIZED — OpenRouter API key is invalid or missing. "
            f"Get a valid key at https://openrouter.ai/keys "
            f"and update OPENROUTER_API_KEY in .env. "
            f"Detail: {full_msg}"
        )
    elif status == 403:
        raise RuntimeError(
            f"FORBIDDEN — Your OpenRouter API key does not have access to this model. "
            f"Check your account at https://openrouter.ai/account "
            f"Detail: {full_msg}"
        )
    elif status == 404:
        raise RuntimeError(
            f"NOT_FOUND — Model or endpoint not found. "
            f"Model used: {_get_model()}. Detail: {full_msg}"
        )
    elif status == 429:
        raise RuntimeError(
            f"QUOTA_EXCEEDED — Too many requests or rate limit hit. "
            f"Detail: {full_msg}"
        )
    elif status == 500:
        raise RuntimeError(f"OPENROUTER_SERVER_ERROR: {full_msg}")
    else:
        raise RuntimeError(f"OPENROUTER_ERROR_{status}: {full_msg}")


# ── Public interface ──────────────────────────────────────────────────────────
def generate_content(prompt: str, system_instruction: str = None,
                     max_retries: int = 2) -> str:
    """
    Generate content via the OpenRouter API with retry logic.
    - 429 QUOTA_EXCEEDED → fail immediately (no retry)
    - Other transient errors → retry up to max_retries with exponential back-off
    Returns the generated text string, or raises RuntimeError.
    """
    for attempt in range(max_retries):
        try:
            return _call_openrouter(prompt, system_instruction)

        except RuntimeError as e:
            err_str = str(e)
            logger.error(
                f"generate_content attempt {attempt + 1}/{max_retries} FAILED: {err_str[:300]}"
            )

            # Non-retryable errors — surface immediately
            if any(tag in err_str for tag in [
                "QUOTA_EXCEEDED", "UNAUTHORIZED", "FORBIDDEN",
                "BAD_REQUEST", "NOT_FOUND",
            ]):
                raise

            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.info(f"Retrying in {wait}s ...")
                time.sleep(wait)
            else:
                logger.error(f"OpenRouter failed after {max_retries} attempts.")
                raise


def check_api_key_status() -> dict:
    """
    Lightweight health-check: sends a minimal chat/completions request.
    Returns {"ok": bool, "error": str|None, "quota_exhausted": bool, ...}
    """
    try:
        key = _get_api_key()
    except RuntimeError as e:
        return {"ok": False, "error": str(e), "quota_exhausted": False}

    model = _get_model()
    try:
        text = _call_openrouter("Reply with exactly one word: OK")
        return {
            "ok":             True,
            "error":          None,
            "quota_exhausted": False,
            "response":       text.strip(),
            "key_prefix":     key[:12] + "...",
            "model":          model,
            "endpoint":       CHAT_COMPLETIONS_URL,
            "provider":       AI_PROVIDER,
        }
    except RuntimeError as e:
        err = str(e)
        is_quota = "QUOTA_EXCEEDED" in err or "429" in err or "quota" in err.lower()
        return {
            "ok":             False,
            "error":          err,
            "quota_exhausted": is_quota,
            "key_prefix":     key[:12] + "...",
            "model":          model,
            "endpoint":       CHAT_COMPLETIONS_URL,
            "provider":       AI_PROVIDER,
        }
