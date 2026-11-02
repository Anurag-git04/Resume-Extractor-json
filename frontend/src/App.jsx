import { useState } from "react";

const SAMPLE = `Rahul Sharma
Python developer with 3 years of experience.

Skills: Python, FastAPI, React, MongoDB
Projects: AI Chatbot (conversational support bot built with FastAPI), Task Manager (React + MongoDB)`;

const API_URL = import.meta.env.VITE_API_URL ?? "";

async function extractResume(resumeText) {
  const res = await fetch(`${API_URL}/api/resume/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_text: resumeText }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI sends {detail: "..."} or, for validation errors, {detail: [{msg}]}
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join("; ") : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return body;
}

function NotFound() {
  return <span className="not-found">Not found in resume</span>;
}

function Field({ label, children }) {
  return (
    <section className="field">
      <h3>{label}</h3>
      <div>{children}</div>
    </section>
  );
}

function FieldsView({ data }) {
  const exp = data.years_of_experience;
  return (
    <div className="fields">
      <Field label="Name">{data.name ?? <NotFound />}</Field>
      <Field label="Professional experience">
        {exp === null || exp === undefined ? <NotFound /> : `${exp} ${exp === 1 ? "year" : "years"}`}
      </Field>
      <Field label="Skills">
        {data.skills.length ? (
          <ul className="chips">
            {data.skills.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <NotFound />
        )}
      </Field>
      <Field label="Projects">
        {data.projects.length ? (
          <ul className="plain">
            {data.projects.map((p) => (
              <li key={p.name}>
                <strong>{p.name}</strong>
                {p.description && <span className="muted"> {p.description}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <NotFound />
        )}
      </Field>
      {data.internships.length > 0 && (
        <Field label="Internships">
          <ul className="plain">
            {data.internships.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </Field>
      )}
    </div>
  );
}

export default function App() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState("fields");
  const [copied, setCopied] = useState(false);

  async function onExtract() {
    setLoading(true);
    setError("");
    try {
      setResult(await extractResume(text));
    } catch (e) {
      setResult(null);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function onCopy() {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const canExtract = text.trim().length >= 20 && !loading;

  return (
    <main className="app">
      <header>
        <h1>Resume-to-JSON Extractor</h1>
        <p>Paste resume text. Anything the resume doesn’t state comes back empty, never guessed.</p>
      </header>

      <div className="panes">
        <section className="pane">
          <div className="pane-head">
            <label htmlFor="resume">Resume text</label>
            <button className="link" onClick={() => setText(SAMPLE)} type="button">
              Use sample
            </button>
          </div>
          <textarea
            id="resume"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the resume here…"
            spellCheck={false}
          />
          <div className="pane-foot">
            <span className="muted">{text.length.toLocaleString()} characters</span>
            <button className="primary" onClick={onExtract} disabled={!canExtract} type="button">
              {loading ? "Extracting…" : "Extract"}
            </button>
          </div>
        </section>

        <section className="pane" aria-live="polite">
          <div className="pane-head">
            <div className="tabs" role="tablist" aria-label="Result view">
              {["fields", "json"].map((v) => (
                <button
                  key={v}
                  role="tab"
                  aria-selected={view === v}
                  className={view === v ? "tab active" : "tab"}
                  onClick={() => setView(v)}
                  type="button"
                >
                  {v === "fields" ? "Fields" : "JSON"}
                </button>
              ))}
            </div>
            {result && view === "json" && (
              <button className="link" onClick={onCopy} type="button">
                {copied ? "Copied" : "Copy JSON"}
              </button>
            )}
          </div>

          <div className="result">
            {error && (
              <div className="error" role="alert">
                <strong>Extraction failed.</strong> {error}
              </div>
            )}
            {!error && !result && !loading && (
              <p className="muted empty">Paste a resume and choose Extract to see the structured result here.</p>
            )}
            {loading && <p className="muted empty">Reading the resume…</p>}
            {result && !loading && (view === "fields" ? <FieldsView data={result} /> : <pre>{JSON.stringify(result, null, 2)}</pre>)}
          </div>
        </section>
      </div>
    </main>
  );
}
