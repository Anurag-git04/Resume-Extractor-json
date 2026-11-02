from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import resume

settings = get_settings()

app = FastAPI(
    title="Resume-to-JSON Extractor",
    description="Paste resume text, get structured candidate data back.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["POST", "GET"],
    allow_headers=["*"]
)

app.include_router(resume.router)

@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "model": settings.groq_model, "groq_key_configured": bool(settings.groq_api_key)}