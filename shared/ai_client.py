"""
shared/ai_client.py — OpenAI wrapper for the SEO_LEAD platform.

Provides two main helpers:
    ask_ai(system, user)       → plain-text response string
    ask_ai_json(system, user)  → parsed dict/list from JSON response

Handles retries, token tracking, and dry-run mock responses.
"""

import json
import time
from typing import Any

from openai import OpenAI

from shared.config import settings
from shared.logger import get_logger

log = get_logger("ai_client")

# ── Cost tracking ────────────────────────────────────────────────────────────
_total_prompt_tokens = 0
_total_completion_tokens = 0
_total_cost_usd = 0.0
_DAILY_SPEND_ALERT = 5.00  # Warn if estimated cost exceeds this

# Approximate pricing per 1M tokens (GPT-4o, as of 2026)
_COST_PER_1M_INPUT = 2.50
_COST_PER_1M_OUTPUT = 10.00


def get_usage_stats() -> dict:
    """Return cumulative token/cost stats for this session."""
    return {
        "prompt_tokens": _total_prompt_tokens,
        "completion_tokens": _total_completion_tokens,
        "total_tokens": _total_prompt_tokens + _total_completion_tokens,
        "estimated_cost_usd": round(_total_cost_usd, 4),
    }

# ── Client singleton ─────────────────────────────────────────────────────────
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


# ── Public API ───────────────────────────────────────────────────────────────

def ask_ai(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.7,
    retries: int = 2,
) -> str:
    """
    Send a chat completion request and return the assistant's text response.

    In dry-run mode, returns a placeholder string instead of calling the API.
    """
    model = model or settings.openai_model
    max_tokens = max_tokens or settings.openai_max_tokens

    if settings.dry_run:
        log.info("[DRY-RUN] Skipping OpenAI call (model=%s)", model)
        return _mock_text_response(system_prompt)

    for attempt in range(1, retries + 2):
        try:
            log.info("OpenAI request (model=%s, attempt=%d)", model, attempt)
            client = _get_client()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = response.choices[0].message.content.strip()

            # Token tracking
            usage = response.usage
            if usage:
                _track_usage(usage.prompt_tokens, usage.completion_tokens)
            return text

        except Exception as exc:
            log.warning("OpenAI error (attempt %d/%d): %s", attempt, retries + 1, exc)
            if attempt > retries:
                raise
            time.sleep(2 ** attempt)  # exponential backoff

    return ""  # unreachable, but keeps type-checkers happy


def ask_ai_json(
    system_prompt: str,
    user_prompt: str,
    **kwargs: Any,
) -> dict | list:
    """
    Like ask_ai(), but expects a JSON response and parses it automatically.

    The system prompt should instruct the model to return valid JSON.
    Strips markdown code fences (```json ... ```) if present.
    """
    if settings.dry_run:
        log.info("[DRY-RUN] Skipping OpenAI JSON call")
        return _mock_json_response(system_prompt)

    raw = ask_ai(system_prompt, user_prompt, **kwargs)
    return _parse_json(raw)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict | list:
    """Parse JSON, stripping optional markdown code fences."""
    cleaned = text.strip()
    # Strip ```json ... ``` wrapper
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        log.error("Failed to parse AI JSON response: %s", exc)
        log.debug("Raw response:\n%s", text[:500])
        raise ValueError(f"AI returned invalid JSON: {exc}") from exc


def _track_usage(prompt_tokens: int, completion_tokens: int) -> None:
    """Accumulate token counts and estimated cost; alert if over budget."""
    global _total_prompt_tokens, _total_completion_tokens, _total_cost_usd
    _total_prompt_tokens += prompt_tokens
    _total_completion_tokens += completion_tokens
    cost = (prompt_tokens * _COST_PER_1M_INPUT + completion_tokens * _COST_PER_1M_OUTPUT) / 1_000_000
    _total_cost_usd += cost
    log.info(
        "Tokens -- prompt: %d, completion: %d | Session total: %d ($%.4f)",
        prompt_tokens, completion_tokens,
        _total_prompt_tokens + _total_completion_tokens, _total_cost_usd,
    )
    if _total_cost_usd >= _DAILY_SPEND_ALERT:
        log.warning(
            "COST ALERT: Estimated session spend $%.2f exceeds $%.2f threshold!",
            _total_cost_usd, _DAILY_SPEND_ALERT,
        )


def _mock_text_response(system_prompt: str) -> str:
    """Return a placeholder text response for dry-run mode."""
    return (
        "[DRY-RUN MOCK RESPONSE]\n"
        "This is a simulated AI response. Run with DRY_RUN=false and valid "
        "API keys to get real results."
    )


def _mock_json_response(system_prompt: str) -> dict:
    """Return a sample JSON structure for dry-run mode."""
    return {
        "_dry_run": True,
        "clusters": [
            {
                "intent": "informational",
                "keywords": [
                    {
                        "keyword": "how to generate leads online",
                        "volume": 3200,
                        "competition": "medium",
                        "opportunity_score": 8,
                    },
                    {
                        "keyword": "lead generation strategies 2026",
                        "volume": 1800,
                        "competition": "low",
                        "opportunity_score": 9,
                    },
                ],
            },
            {
                "intent": "transactional",
                "keywords": [
                    {
                        "keyword": "best lead generation software",
                        "volume": 4500,
                        "competition": "high",
                        "opportunity_score": 6,
                    },
                ],
            },
        ],
    }
