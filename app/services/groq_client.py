import groq

from app.config import Settings
from app.services.extractor import LLMCall, LLMUnavailableError, Message


def make_groq_llm_call(settings: Settings) -> LLMCall:
    client = groq.AsyncGroq(
        api_key=settings.groq_api_key,
        timeout=settings.groq_timeout_seconds,
        max_retries=2,
    )

    async def call(messages: list[Message]) -> str:
        try:
            response = await client.chat.completions.create(
                model=settings.groq_model,
                messages=messages,
                temperature=0,  # extraction should be deterministic
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
        except groq.GroqError as exc:
            raise LLMUnavailableError(f"Groq request failed: {exc.__class__.__name__}") from exc
        return response.choices[0].message.content or ""

    return call
