import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.routes.resume import get_extractor
from app.schemas.resume import ResumeData, Project
from app.services.extractor import ExtractionError, LLMUnavailableError

TEXT = "Name: Rahul Sharma. Python developer with 3 years of experience. Skills: Python, FastAPI."


class FakeExtractor:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    async def extract(self, text):
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use(extractor):
    app.dependency_overrides[get_extractor] = lambda: extractor


def test_extract_success(client):
    use(FakeExtractor(ResumeData(name="Rahul Sharma", skills=["Python"], years_of_experience=3,
                                 projects=[Project(name="AI Chatbot")])))
    r = client.post("/api/resume/extract", json={"resume_text": TEXT})
    assert r.status_code == 200
    assert r.json()["name"] == "Rahul Sharma"
    assert r.json()["years_of_experience"] == 3


def test_missing_fields_serialize_as_null(client):
    use(FakeExtractor(ResumeData()))
    body = client.post("/api/resume/extract", json={"resume_text": TEXT}).json()
    assert body["name"] is None and body["years_of_experience"] is None
    assert body["skills"] == [] and body["projects"] == []


def test_rejects_too_short_text(client):
    use(FakeExtractor(ResumeData()))
    assert client.post("/api/resume/extract", json={"resume_text": "hi"}).status_code == 422


def test_rejects_missing_field(client):
    use(FakeExtractor(ResumeData()))
    assert client.post("/api/resume/extract", json={}).status_code == 422


def test_rejects_oversized_text(client):
    use(FakeExtractor(ResumeData()))
    app.dependency_overrides[get_settings] = lambda: Settings(max_resume_chars=50, groq_api_key="x")
    r = client.post("/api/resume/extract", json={"resume_text": "a" * 200})
    assert r.status_code == 413


@pytest.mark.parametrize("error", [ExtractionError("bad output"), LLMUnavailableError("down")])
def test_upstream_failures_return_502(client, error):
    use(FakeExtractor(error=error))
    assert client.post("/api/resume/extract", json={"resume_text": TEXT}).status_code == 502


def test_missing_api_key_returns_503(client):
    app.dependency_overrides[get_settings] = lambda: Settings(groq_api_key="")
    r = client.post("/api/resume/extract", json={"resume_text": TEXT})
    assert r.status_code == 503
