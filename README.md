# Resume-to-JSON Extractor

Paste resume text, get structured candidate data back. Built with **FastAPI + Groq + Pydantic**, with an optional **React** UI.

```json
{
  "name": "Rahul Sharma",
  "skills": ["Python", "FastAPI", "React", "MongoDB"],
  "years_of_experience": 3,
  "projects": [{"name": "AI Chatbot", "description": null}, {"name": "Task Manager", "description": null}],
  "internships": []
}
```

Rule #1: **never assume**. Anything the resume doesn't state comes back as `null` (or `[]`), and professional experience is kept separate from internships and projects.

## Run the backend

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then put your key in GROQ_API_KEY (https://console.groq.com/keys)
uvicorn app.main:app --reload      # http://localhost:8000/docs
```

Try it:

```bash
curl -X POST http://localhost:8000/api/resume/extract \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "Name: Rahul Sharma. Python developer with 3 years of experience. Skills: Python, FastAPI, React, MongoDB. Projects: AI Chatbot and Task Manager."}'
```

In Postman: `POST http://localhost:8000/api/resume/extract`, body → raw → JSON, `{"resume_text": "..."}`.

## Run the frontend (optional)

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173 (proxies /api to :8000)
```

## Run the tests

```bash
pytest
```

The tests use a fake LLM, so they need no API key and no network.

## How it works

```
POST /api/resume/extract
  -> ResumeRequest (Pydantic: trims, rejects text < 20 chars)
  -> ResumeExtractor.extract()
       1. Groq chat completion, temperature 0, JSON mode, strict system prompt
       2. parse JSON (tolerates ```json fences) + validate with ResumeData
       3. on invalid output: one retry that feeds the validation error back to the model
       4. post-process: normalize skills ("react.js" -> "React"), de-duplicate, then
          drop any skill or name that does not literally appear in the resume text
  -> ResumeData JSON
```

| Failure | Status |
|---|---|
| Missing/short `resume_text` | 422 |
| Resume over `MAX_RESUME_CHARS` | 413 |
| Groq unreachable, or still invalid after retry | 502 |
| `GROQ_API_KEY` not set | 503 |

## Edge cases and where they are handled

| Case | Handling |
|---|---|
| No name in resume | Prompt rule + grounding check → `name: null` |
| Experience not stated | Prompt rule → `years_of_experience: null` |
| Skills only in project text | Prompt asks for explicitly named skills from anywhere in the resume |
| Overlapping tech across projects | Case-insensitive de-duplication of skills; projects de-duped by name |
| Fresher with internships | Internships go in `internships`, never in `years_of_experience` |
| Dates but no total | Model sums closed date ranges only; any "present" role → `null` (it can't know today's date) |
| Hallucinated skill/name | Dropped in post-processing if it isn't in the source text |
| Prompt injection inside resume | Resume is wrapped in `<resume>` tags and declared untrusted data |

## Project layout

```
app/
  main.py               FastAPI app, CORS, /health
  config.py             settings from .env
  routes/resume.py      POST /api/resume/extract
  services/extractor.py prompt -> parse -> validate -> retry -> post-process
  services/groq_client.py  thin Groq wrapper (swap this to change provider)
  schemas/resume.py     Pydantic models
  utils/prompts.py      system / user / retry prompts
  utils/normalize.py    skill aliases + grounding check
tests/                  pytest suite (fake LLM)
frontend/               Vite + React UI
```

## Notes

- `GROQ_MODEL` defaults to `llama-3.3-70b-versatile`. Groq changes its model lineup over time, so check https://console.groq.com/docs/models if you get a "model not found" error.
- `years_of_experience` can be fractional (e.g. `2.5`); whole numbers are returned as integers.
- Ideas to extend: PDF/DOCX upload (`pdfplumber`, `python-docx`), education and certifications fields, a `/batch` endpoint, response caching by text hash.
