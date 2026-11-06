import logging

import groq

from app.config import Settings
from app.services.extractor import LLMCall, LLMUnavailableError, Message

logger = logging.getLogger(__name__)


def make_groq_llm_call(settings: Settings) -> LLMCall:
    client = groq.AsyncGroq(
        api_key=settings.groq_api_key,
        timeout=settings.groq_timeout_seconds,
        max_retries=2,
    )
    is_reasoning_model = "gpt-oss" in settings.groq_model

    async def call(messages: list[Message]) -> str:
        kwargs = dict(
            model=settings.groq_model,
            messages=messages,
            temperature=0,       # extraction should be deterministic
            max_tokens=4096,     # was 1500: room for long resumes and reasoning
        )
        if is_reasoning_model:
            kwargs["extra_body"] = {"reasoning_effort": "low"}  # keep thinking short

        try:
            try:
                response = await client.chat.completions.create(
                    **kwargs, response_format={"type": "json_object"}
                )
            except groq.BadRequestError as exc:
                if "json_validate_failed" not in str(exc):
                    raise
                # JSON mode produced nothing valid. Retry as plain text: our own parser
                # strips ```json fences and Pydantic validates the result.
                logger.warning("Groq JSON mode failed; retrying without it")
                response = await client.chat.completions.create(**kwargs)
        except groq.APIStatusError as exc:
            logger.error("Groq returned HTTP %s: %s", exc.status_code, exc.message)
            raise LLMUnavailableError(f"Groq returned HTTP {exc.status_code}: {exc.message}") from exc
        except groq.GroqError as exc:
            logger.error("Groq request failed: %r", exc)
            raise LLMUnavailableError(f"Groq request failed: {exc.__class__.__name__}") from exc

        return response.choices[0].message.content or ""

    return call