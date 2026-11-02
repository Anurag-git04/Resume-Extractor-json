from app.utils.normalize import appears_in_text, normalize_skills


def test_normalizes_and_dedupes():
    assert normalize_skills(["react.js", "React", "nodejs", "Node.js", "  fastapi "]) == ["React", "Node.js", "FastAPI"]


def test_unknown_skills_kept_as_written():
    assert normalize_skills(["Pandas"]) == ["Pandas"]


def test_grounding_variants():
    assert appears_in_text("React.js", "Built UIs with React and Redux")
    assert appears_in_text("Node.js", "backend in NodeJS")
    assert not appears_in_text("Kubernetes", "Skills: Python, FastAPI")


def test_grounding_uses_word_boundaries():
    assert not appears_in_text("Java", "Skills: JavaScript")
    assert appears_in_text("C++", "Languages: C++, Python")
