import json
import re
from typing import Awaitable, Callable

from pydantic import ValidationError

from app.schemas.resume import ResumeData
from app.utils.normalize import appears_in_text, normalize_skills
from app.utils.prompts import RETRY_PROMPT_TEMPLATE, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

Message = dict[str, str]
# Takes chat messages, returns the model's raw text reply.
LLMCall = Callable[[list[Message]], Awaitable[str]]


class LLMUnavailableError(Exception):
    """The LLM provider could not be reached or rejected the request."""


class ExtractionError(Exception):
    """The LLM replied, but never with output that passed validation."""


def parse_json_object(raw: str) -> dict:
    """Parse a JSON object from a model reply, tolerating ```json fences and stray text."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("reply did not contain a JSON object")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")
    return data


class ResumeExtractor:
    def __init__(self, llm_call: LLMCall, max_attempts: int = 2):
        self._llm_call = llm_call
        self._max_attempts = max_attempts

    async def extract(self, resume_text: str) -> ResumeData:
        messages: list[Message] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(resume_text=resume_text)},
        ]
        last_error = "unknown error"

        for _ in range(self._max_attempts):
            raw = await self._llm_call(messages)
            try:
                parsed = ResumeData.model_validate(parse_json_object(raw))
            except (ValueError, ValidationError) as exc:  # JSONDecodeError is a ValueError
                last_error = str(exc)[:500]
                messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": RETRY_PROMPT_TEMPLATE.format(error=last_error)},
                ]
                continue
            return self._postprocess(parsed, resume_text)

        raise ExtractionError(f"Model did not return valid JSON after {self._max_attempts} attempts: {last_error}")

    @staticmethod
    def _postprocess(data: ResumeData, resume_text: str) -> ResumeData:
        """Normalize and ground the output in the source text ("never assume")."""
        # Name: every token must literally appear in the resume.
        if data.name:
            tokens = re.findall(r"\w+", data.name)
            if not tokens or not all(appears_in_text(t, resume_text) for t in tokens):
                data.name = None

        # Skills: canonical spelling, de-duplicated, and must be present in the text.
        data.skills = [s for s in normalize_skills(data.skills) if appears_in_text(s, resume_text)]

        # Projects: drop duplicates by name.
        seen: set[str] = set()
        unique = []
        for p in data.projects:
            key = p.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        data.projects = unique

        data.internships = [i.strip() for i in data.internships if i and i.strip()]
        return data