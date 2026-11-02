import json

import pytest

from app.services.extractor import ExtractionError, ResumeExtractor

RESUME = (
    "Name: Rahul Sharma. Python developer with 3 years of experience. "
    "Skills: Python, FastAPI, React, MongoDB. Projects: AI Chatbot and Task Manager."
)


def fake_llm(*replies: str):
    """Returns an llm_call that yields the given replies in order and records calls."""
    calls: list = []
    queue = list(replies)

    async def call(messages):
        calls.append(messages)
        return queue.pop(0)

    call.calls = calls
    return call


GOOD = {
    "name": "Rahul Sharma",
    "skills": ["Python", "FastAPI", "React", "MongoDB"],
    "years_of_experience": 3.0,
    "projects": [{"name": "AI Chatbot"}, {"name": "Task Manager"}],
    "internships": [],
}


async def test_happy_path():
    result = await ResumeExtractor(fake_llm(json.dumps(GOOD))).extract(RESUME)
    assert result.name == "Rahul Sharma"
    assert result.skills == ["Python", "FastAPI", "React", "MongoDB"]
    assert result.years_of_experience == 3 and isinstance(result.years_of_experience, int)
    assert [p.name for p in result.projects] == ["AI Chatbot", "Task Manager"]


async def test_accepts_markdown_fenced_json():
    reply = "```json\n" + json.dumps(GOOD) + "\n```"
    result = await ResumeExtractor(fake_llm(reply)).extract(RESUME)
    assert result.name == "Rahul Sharma"


async def test_retries_once_on_invalid_reply():
    llm = fake_llm("Sure! Here is the data", json.dumps(GOOD))
    result = await ResumeExtractor(llm).extract(RESUME)
    assert result.name == "Rahul Sharma"
    assert len(llm.calls) == 2
    assert "invalid" in llm.calls[1][-1]["content"]


async def test_raises_after_repeated_failures():
    with pytest.raises(ExtractionError):
        await ResumeExtractor(fake_llm("nope", "still nope")).extract(RESUME)


async def test_schema_violation_triggers_retry():
    bad = {**GOOD, "years_of_experience": -5}
    llm = fake_llm(json.dumps(bad), json.dumps(GOOD))
    result = await ResumeExtractor(llm).extract(RESUME)
    assert result.years_of_experience == 3


async def test_hallucinated_name_becomes_null():
    reply = json.dumps({**GOOD, "name": "John Smith"})
    result = await ResumeExtractor(fake_llm(reply)).extract(RESUME)
    assert result.name is None


async def test_hallucinated_skills_are_dropped():
    reply = json.dumps({**GOOD, "skills": ["Python", "Kubernetes", "react.js"]})
    result = await ResumeExtractor(fake_llm(reply)).extract(RESUME)
    assert result.skills == ["Python", "React"]


async def test_unknown_experience_stays_null():
    text = "Priya Nair. Skills: Python. Intern at Acme, Jan-Mar 2024."
    reply = json.dumps(
        {"name": "Priya Nair", "skills": ["Python"], "years_of_experience": None,
         "projects": [], "internships": ["Intern at Acme (3 months)"]}
    )
    result = await ResumeExtractor(fake_llm(reply)).extract(text)
    assert result.years_of_experience is None
    assert result.internships == ["Intern at Acme (3 months)"]


async def test_duplicate_projects_removed():
    reply = json.dumps({**GOOD, "projects": [{"name": "AI Chatbot"}, {"name": "ai chatbot"}]})
    result = await ResumeExtractor(fake_llm(reply)).extract(RESUME)
    assert len(result.projects) == 1
