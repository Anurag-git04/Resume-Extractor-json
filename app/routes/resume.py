from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.schemas.resume import ResumeData, ResumeRequest
from app.services.extractor import ExtractionError, LLMUnavailableError, ResumeExtractor
from app.services.groq_client import make_groq_llm_call

router = APIRouter(prefix="/api/resume", tags=["resume"])


@lru_cache
def _build_extractor(api_key: str, model: str) -> ResumeExtractor:
    # keyed on settings so tests / reloads never reuse a stale client
    return ResumeExtractor(make_groq_llm_call(get_settings()))


def get_extractor(settings: Settings = Depends(get_settings)) -> ResumeExtractor:
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the server.")
    return _build_extractor(settings.groq_api_key, settings.groq_model)


@router.post("/extract", response_model=ResumeData)
async def extract_resume(
    payload: ResumeRequest,
    extractor: ResumeExtractor = Depends(get_extractor),
    settings: Settings = Depends(get_settings),
) -> ResumeData:
    if len(payload.resume_text) > settings.max_resume_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Resume is too long (max {settings.max_resume_chars} characters).",
        )
    try:
        return await extractor.extract(payload.resume_text)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
