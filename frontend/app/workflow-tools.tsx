"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Conversation, Requirement, Training, Domain } from "./types";

export function DiscoveryBrief({
  onCreated,
}: {
  onCreated: (c: Conversation) => void;
}) {
  const [context, setContext] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Start from a customer brief</h2>
      </div>
      <div className="panel-body">
        <p>
          Describe a fictional customer's workflow, constraints and unanswered
          questions. A recording is optional.
        </p>
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError("");
            try {
              onCreated(
                await api<Conversation>("/sales/discovery", {
                  title: "Synthetic customer discovery",
                  context,
                  synthetic_consent: true,
                }),
              );
            } catch (e) {
              setError(e instanceof Error ? e.message : "Discovery failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          <textarea
            aria-label="Synthetic customer brief"
            placeholder="Our refurbishment team needs device QR history. Partners must not see owner details. Our ERP version is not yet confirmed…"
            value={context}
            onChange={(e) => setContext(e.target.value)}
          />
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            This brief contains fictional, synthetic customer information.
          </label>
          <button
            className="primary"
            disabled={busy || !consent || context.trim().length < 10}
          >
            {busy ? "Analysing customer brief…" : "Build discovery workspace"}
          </button>
          {error && (
            <p role="alert" className="note danger">
              {error}
            </p>
          )}
        </form>
      </div>
    </section>
  );
}

export function PitchControls({
  cid,
  onPitch,
}: {
  cid: string;
  onPitch: (pitch: string) => void;
}) {
  const [language, setLanguage] = useState("Hinglish");
  const [familiarity, setFamiliarity] = useState("business");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <div className="note">
      <div className="inline">
        <select
          aria-label="Pitch language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option>Hinglish</option>
          <option>Hindi</option>
          <option>English</option>
        </select>
        <select
          aria-label="Pitch audience"
          value={familiarity}
          onChange={(e) => setFamiliarity(e.target.value)}
        >
          <option value="business">Business audience</option>
          <option value="technical">Technical audience</option>
        </select>
        <button
          className="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              const result = await api<{ pitch: string }>(
                `/conversations/${cid}/pitch`,
                { language, familiarity },
              );
              onPitch(result.pitch);
            } catch (e) {
              setError(String(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          Adapt pitch
        </button>
      </div>
      <small>
        Uses approved source wording; technical checklists remain in source
        English. Review your edited pitch before sharing.
      </small>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

export function AcademyHistory({
  revision,
  onOpen,
}: {
  revision: string;
  onOpen: (session: Training) => void;
}) {
  const [sessions, setSessions] = useState<
    { id: string; scenario: string; complete: boolean; turns: number }[]
  >([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<typeof sessions>("/training/sessions")
      .then((data) => {
        if (active) setSessions(data);
      })
      .catch((e) => {
        if (active) setError(String(e));
      });
    return () => {
      active = false;
    };
  }, [revision]);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Practice history</h2>
      </div>
      <div className="panel-body">
        {sessions.length ? (
          sessions.map((s) => (
            <button
              key={s.id}
              className="secondary"
              onClick={async () => {
                try {
                  onOpen(await api<Training>("/training/sessions/" + s.id));
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              {s.scenario} · {s.turns}/3 turns ·{" "}
              {s.complete ? "Review scorecard" : "Resume"}
            </button>
          ))
        ) : (
          <p>No practice sessions yet.</p>
        )}
        {error && <p role="alert">{error}</p>}
      </div>
    </section>
  );
}

export function RequirementThemes({
  requirements,
}: {
  requirements: Requirement[];
}) {
  const active = requirements.filter((r) => !r.superseded_by?.length);
  const categories = Array.from(new Set(active.map((r) => r.category)));
  const pairs = active.flatMap((r, index) =>
    active
      .slice(index + 1)
      .filter(
        (other) => !!r.capability_id && r.capability_id === other.capability_id,
      )
      .map((other) => `${r.id} and ${other.id}`),
  );
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Requirement themes</h2>
      </div>
      <div className="panel-body">
        {categories.map((category) => (
          <details key={category}>
            <summary>
              {category.replaceAll("_", " ")} ·{" "}
              {active.filter((r) => r.category === category).length}
            </summary>
            <ul>
              {active
                .filter((r) => r.category === category)
                .map((r) => (
                  <li key={r.id}>
                    {r.id}: {r.title}
                  </li>
                ))}
            </ul>
          </details>
        ))}
        {pairs.length > 0 && (
          <div className="note">
            <strong>Possible overlaps to review</strong>
            {pairs.map((pair) => (
              <p key={pair}>
                {pair}: shared capability; compare evidence before using
                merge/split below.
              </p>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export function CommunicationExperiment() {
  type Experiment = {
    design: string;
    persona: string;
    objection: string;
    strategies: { id: string; name: string; pitch: string }[];
    runs: { id: string; strategy_id: string; outcome: string; quote: string }[];
    caveat: string;
  };
  const [data, setData] = useState<Experiment | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Experiment>("/insights/experiment")
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Controlled scripted pitch comparison</h2>
      </div>
      <div className="panel-body">
        {data && (
          <>
            <p className="note">{data.design}</p>
            <p>{data.persona}</p>
            <p>
              <strong>Same objection:</strong> {data.objection}
            </p>
            <div className="two-col">
              {data.strategies.map((strategy) => (
                <div key={strategy.id}>
                  <h3>{strategy.name}</h3>
                  <p>{strategy.pitch}</p>
                  <p>
                    Sample:{" "}
                    {
                      data.runs.filter((run) => run.strategy_id === strategy.id)
                        .length
                    }{" "}
                    authored runs
                  </p>
                  {data.runs
                    .filter((run) => run.strategy_id === strategy.id)
                    .map((run) => (
                      <blockquote key={run.id}>
                        <strong>{run.outcome.replaceAll("_", " ")}</strong>
                        <p>“{run.quote}”</p>
                        <small>Scripted evidence {run.id}</small>
                      </blockquote>
                    ))}
                </div>
              ))}
            </div>
            <p className="muted">{data.caveat}</p>
          </>
        )}
        {error && <p role="alert">{error}</p>}
      </div>
    </section>
  );
}

export function AudioObservations({ cid }: { cid: string }) {
  const [data, setData] = useState<{
    duration_seconds: number;
    transcript_tokens_per_minute?: number;
    pace_caveat?: string;
    mean_volume_dbfs: number | null;
    silence_spans: { start_ms: number; end_ms: number }[];
    caveat: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setData(null);
    setError("");
  }, [cid]);
  return (
    <div className="note">
      <button
        className="secondary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            setData(await api(`/conversations/${cid}/acoustics`, {}));
          } catch (e) {
            setError(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Measuring audio…" : "Measure uploaded audio energy & pauses"}
      </button>
      {data && (
        <>
          <p>
            {data.duration_seconds}s audio · mean energy{" "}
            {data.mean_volume_dbfs ?? "unavailable"} dBFS ·{" "}
            {data.silence_spans.length} low-energy spans
          </p>
          {data.transcript_tokens_per_minute !== undefined && (
            <p>
              Transcript token pace: {data.transcript_tokens_per_minute}/minute.{" "}
              {data.pace_caveat}
            </p>
          )}
          <details>
            <summary>Measured timestamp spans</summary>
            {data.silence_spans.map((span, i) => (
              <p key={i}>
                {(span.start_ms / 1000).toFixed(2)}–
                {(span.end_ms / 1000).toFixed(2)}s
              </p>
            ))}
          </details>
          <p>{data.caveat}</p>
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

export function KnowledgeDrafts({
  role,
  domainId = "synthetic-device-lifecycle",
  onApproved,
}: {
  role: string;
  domainId?: Domain;
  onApproved: () => void;
}) {
  const [title, setTitle] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [keywords, setKeywords] = useState("");
  const [capability, setCapability] = useState("");
  const [status, setStatus] = useState("unknown");
  const [criteria, setCriteria] = useState("");
  const [dependencies, setDependencies] = useState("");
  const [consent, setConsent] = useState(false);
  const [drafts, setDrafts] = useState<
    { id: string; title: string; excerpt: string }[]
  >([]);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = () =>
    api<typeof drafts>("/knowledge/drafts?domain_id=" + domainId).then(
      setDrafts,
    );
  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Add a synthetic product source</h2>
      </div>
      <div className="panel-body">
        <details>
          <summary>Create a documentation draft</summary>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              setError("");
              try {
                await api("/knowledge/documents", {
                  title,
                  domain_id: domainId,
                  excerpt,
                  keywords: keywords
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                  capability_id: capability.trim() || null,
                  status_value: status,
                  criteria: criteria.split("\n").filter(Boolean),
                  dependencies: dependencies.split("\n").filter(Boolean),
                  synthetic_consent: consent,
                });
                setTitle("");
                setExcerpt("");
                await refresh();
              } catch (e) {
                setError(String(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Source title
              <input
                required
                minLength={3}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Approved facts and limitations
              <textarea
                required
                minLength={20}
                value={excerpt}
                onChange={(e) => setExcerpt(e.target.value)}
              />
            </label>
            <label>
              Search keywords, separated by commas
              <input
                required
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
              />
            </label>
            <label>
              New capability ID (optional; leave blank for supplementary
              documentation)
              <input
                value={capability}
                onChange={(e) => setCapability(e.target.value)}
                placeholder="weekly-export"
              />
            </label>
            <label>
              Documented support status
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="unknown">Unknown</option>
                <option value="conditional">Conditional</option>
                <option value="supported">Supported</option>
                <option value="unsupported">Unsupported</option>
              </select>
            </label>
            <label>
              Acceptance checks, one per line
              <textarea
                value={criteria}
                onChange={(e) => setCriteria(e.target.value)}
              />
            </label>
            <label>
              Dependencies and conditions, one per line
              <textarea
                value={dependencies}
                onChange={(e) => setDependencies(e.target.value)}
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />{" "}
              This document describes a synthetic demo product.
            </label>
            <button className="primary" disabled={busy || !consent}>
              Save source draft
            </button>
          </form>
        </details>
        {drafts.map((draft) => (
          <div className="note" key={draft.id}>
            <h3>{draft.title}</h3>
            <p>{draft.excerpt}</p>
            <label>
              Review rationale
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="How were these facts and limitations verified?"
              />
            </label>
            <button
              className="secondary"
              disabled={
                busy ||
                role !== "Technical Reviewer" ||
                reason.trim().length < 10
              }
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  await api(
                    `/knowledge/documents/${draft.id}/approve`,
                    { reason },
                    role,
                  );
                  await refresh();
                  onApproved();
                } catch (e) {
                  setError(String(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Approve source for retrieval
            </button>
          </div>
        ))}
        <p className="muted">
          Drafts cannot influence answers or assessments. Approval requires the
          Technical Reviewer demo role. Existing conversations keep their
          snapshots; reanalyse to include new sources.
        </p>
        {error && <p role="alert">{error}</p>}
      </div>
    </section>
  );
}

export function AcademyKnowledge({
  domainId = "synthetic-device-lifecycle",
  renderSources,
}: {
  domainId?: Domain;
  renderSources: (ids: string[]) => React.ReactNode;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{
    status: string;
    answer: string;
    sources: string[];
  } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Product knowledge assistant</h2>
      </div>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          try {
            setAnswer(
              await api("/sales/ask", { question, domain_id: domainId }),
            );
          } catch (e) {
            setError(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Practice product question
          <textarea
            aria-label="Practice product question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Can a repair partner see owner details?"
          />
        </label>
        <button className="secondary" disabled={busy || !question.trim()}>
          Ask approved product knowledge
        </button>
      </form>
      {answer && (
        <div className="note">
          <strong>{answer.status}</strong>
          <p>{answer.answer}</p>
          {renderSources(answer.sources)}
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
