"""Skill normalization and grounding helpers (no LLM involved)."""
import re

# lowercase variant -> canonical display name
SKILL_ALIASES: dict[str, str] = {
    "reactjs": "React", "react.js": "React", "react": "React",
    "nextjs": "Next.js", "next.js": "Next.js",
    "nodejs": "Node.js", "node.js": "Node.js", "node": "Node.js",
    "expressjs": "Express.js", "express.js": "Express.js", "express": "Express.js",
    "vuejs": "Vue.js", "vue.js": "Vue.js", "vue": "Vue.js",
    "angularjs": "Angular", "angular": "Angular",
    "js": "JavaScript", "javascript": "JavaScript",
    "ts": "TypeScript", "typescript": "TypeScript",
    "python3": "Python", "python": "Python",
    "fastapi": "FastAPI", "fast api": "FastAPI",
    "mongo": "MongoDB", "mongodb": "MongoDB", "mongo db": "MongoDB",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "sqlite": "SQLite",
    "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
    "aws": "AWS", "amazon web services": "AWS",
    "html5": "HTML", "html": "HTML", "css3": "CSS", "css": "CSS",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS", "tailwind css": "Tailwind CSS",
    "k8s": "Kubernetes", "kubernetes": "Kubernetes",
    "rest": "REST APIs", "rest api": "REST APIs", "rest apis": "REST APIs", "restful api": "REST APIs",
    "llm": "LLMs", "llms": "LLMs",
}


def normalize_skill(raw: str) -> str:
    cleaned = " ".join(raw.strip().split())
    return SKILL_ALIASES.get(cleaned.lower(), cleaned)


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize spelling and drop case-insensitive duplicates, keeping first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for s in skills:
        if not isinstance(s, str) or not s.strip():
            continue
        canon = normalize_skill(s)
        key = canon.lower()
        if key not in seen:
            seen.add(key)
            out.append(canon)
    return out


def _variants(term: str) -> set[str]:
    """Spellings of a skill that count as 'present in the text'."""
    t = term.strip().lower()
    canon = normalize_skill(term).lower()
    variants = {t, canon}
    for alias, name in SKILL_ALIASES.items():
        if name.lower() == canon:
            variants.add(alias)
    return variants


def appears_in_text(term: str, text: str) -> bool:
    """True if `term` (or a known variant) occurs as a whole word/phrase in `text`."""
    haystack = text.lower()
    for v in _variants(term):
        if re.search(rf"(?<![a-z0-9]){re.escape(v)}(?![a-z0-9])", haystack):
            return True
    return False
