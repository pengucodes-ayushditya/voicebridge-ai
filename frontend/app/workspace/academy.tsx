"use client";
import { useEffect, useState } from "react";
import { ArrowRight, GraduationCap, Send, Sparkles } from "lucide-react";
import { api } from "../api";
import { AcademyKnowledge } from "../workflow-tools";
import type { Domain, Scenario, Training } from "../types";
import { useWorkspace } from "./context";
import { Badge, DetailList, Panel, Sources } from "./ui";
export function Academy() {
  const { domain, setDomain, busy, run, providers, kb } = useWorkspace();
  const [scenarios, setScenarios] = useState<Scenario[]>([]),
    [session, setSession] = useState<Training | null>(null),
    [text, setText] = useState(""),
    [history, setHistory] = useState<
      {
        id: string;
        scenario: string;
        complete: boolean;
        turns: number;
        domain_id?: Domain;
      }[]
    >([]);
  useEffect(() => {
    void api<Scenario[]>("/training/scenarios")
      .then(setScenarios)
      .catch(() => {});
  }, []);
  useEffect(() => {
    void api<typeof history>("/training/sessions")
      .then(setHistory)
      .catch(() => {});
  }, [session?.id, session?.turns.length]);
  useEffect(() => {
    setSession(null);
    setText("");
  }, [domain]);
  async function start(id: string) {
    const result = await run("Starting the practice scenario", () =>
      api<Training>("/training/sessions", { scenario_id: id }),
    );
    if (result) {
      setSession(result);
      setText("");
    }
  }
  async function coach(id: string) {
    const result = await run(
      "Reviewing your actual wording with product knowledge",
      () => api<Training>(`/training/sessions/${id}/coach`, {}),
    );
    if (result) setSession(result);
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!session || !text.trim()) return;
    const result = await run("Saving your practice turn", () =>
      api<Training>(`/training/sessions/${session.id}/turns`, { text }),
    );
    if (result) {
      setSession(result);
      setText("");
      if (result.complete && providers?.reasoning.configured)
        await coach(result.id);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">SALES ACADEMY</span>
          <h1>
            Practice the conversation.
            <br />
            Improve the next one.
          </h1>
          <p>
            Three-turn customer scenarios, grounded product knowledge and
            feedback on your actual words.
          </p>
        </div>
        <label className="compact-label">
          Practice product
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value as Domain)}
          >
            <option value="marketplace">Marketplace intelligence</option>
            <option value="synthetic-device-lifecycle">
              Device lifecycle & repair
            </option>
          </select>
        </label>
      </div>
      <div className="scenario-grid">
        {scenarios
          .filter(
            (s) => (s.domain_id || "synthetic-device-lifecycle") === domain,
          )
          .map((s) => (
            <button
              key={s.id}
              className={
                "scenario-card " +
                (session?.scenario.id === s.id ? "selected" : "")
              }
              disabled={!!busy}
              onClick={() => start(s.id)}
            >
              <GraduationCap size={24} />
              <h2>{s.name}</h2>
              <p>{s.persona}</p>
              <span className="small">{s.objective}</span>
              <strong>
                Start practice <ArrowRight size={14} />
              </strong>
            </button>
          ))}
      </div>
      <div className="academy-layout">
        <div>
          <Panel
            title={
              session ? session.scenario.name : "Choose a scenario to begin"
            }
            eyebrow="SCRIPTED CUSTOMER · THREE PRACTICE TURNS"
            action={
              session && (
                <Badge tone={session.complete ? "green" : ""}>
                  {session.turns.length}/3 turns
                </Badge>
              )
            }
          >
            {session ? (
              <>
                <p className="muted">{session.scenario.objective}</p>
                <div className="practice-chat">
                  {session.turns.map((turn, i) => (
                    <div key={i}>
                      <div className="practice-bubble customer">
                        <span>Customer</span>
                        <p>{turn.customer}</p>
                      </div>
                      <div className="practice-bubble trainee">
                        <span>Your response</span>
                        <p>{turn.trainee}</p>
                      </div>
                    </div>
                  ))}
                  {!session.complete && (
                    <div className="practice-bubble customer">
                      <span>Customer</span>
                      <p>{session.question}</p>
                    </div>
                  )}
                </div>
                {!session.complete ? (
                  <form onSubmit={submit}>
                    <label>
                      Your response
                      <textarea
                        rows={4}
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Explain what is documented, acknowledge the concern and ask a useful question."
                      />
                    </label>
                    <button
                      className="primary"
                      disabled={!!busy || !text.trim()}
                    >
                      <Send size={15} />
                      Send practice response
                    </button>
                  </form>
                ) : (
                  <div className="inline spread">
                    <Badge tone="green">Scenario complete</Badge>
                    <button
                      className="secondary"
                      disabled={!!busy || !providers?.reasoning.configured}
                      onClick={() => coach(session.id)}
                    >
                      <Sparkles size={15} />
                      {session.ai_coaching
                        ? "Refresh AI coaching"
                        : "Get AI coaching"}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="academy-empty">
                <GraduationCap size={38} />
                <p>
                  Select a customer persona above. You will practise discovery,
                  product explanations and honest commitments.
                </p>
              </div>
            )}
          </Panel>
          {session?.ai_coaching && (
            <Panel
              title="Your coaching, with evidence"
              eyebrow="AI PRACTICE FEEDBACK"
            >
              <p className="coaching-summary">{session.ai_coaching.summary}</p>
              <DetailList
                title="What worked"
                items={session.ai_coaching.strengths}
              />
              <DetailList
                title="Practise next"
                items={session.ai_coaching.next_practice}
              />
              {session.ai_coaching.examples.map((example, i) => (
                <article className="coaching-example" key={i}>
                  <Badge>Turn {example.turn}</Badge>
                  <blockquote>“{example.quote}”</blockquote>
                  <p>{example.feedback}</p>
                  <div className="suggested-wording">
                    <span className="eyebrow">TRY THIS WORDING</span>
                    <p>{example.alternative}</p>
                  </div>
                  <Sources ids={example.source_ids} />
                </article>
              ))}
              <p className="provenance">
                {session.ai_coaching.provider} · {session.ai_coaching.caveat}
              </p>
            </Panel>
          )}
          {session?.evaluation && (
            <details className="advanced-panel">
              <summary>Transparent rule-based scorecard</summary>
              <div className="advanced-body">
                <p className="muted">{session.evaluation.caveat}</p>
                {session.evaluation.rubric.map((item, i) => (
                  <div className="rubric-row" key={i}>
                    <div>
                      <strong>{item.category}</strong>
                      <p>{item.rationale}</p>
                    </div>
                    <b>
                      {item.score}
                      <span>/5</span>
                    </b>
                  </div>
                ))}
                {session.evaluation.examples.map((example, i) => (
                  <article className="coaching-example" key={i}>
                    <blockquote>{example.quote}</blockquote>
                    <p>{example.feedback}</p>
                    <p>
                      <strong>Suggested alternative:</strong>{" "}
                      {example.alternative}
                    </p>
                  </article>
                ))}
                <Sources ids={session.evaluation.sources} />
              </div>
            </details>
          )}
        </div>
        <aside>
          <Panel title="Practice history">
            {history.filter(
              (h) => (h.domain_id || "synthetic-device-lifecycle") === domain,
            ).length ? (
              history
                .filter(
                  (h) =>
                    (h.domain_id || "synthetic-device-lifecycle") === domain,
                )
                .slice()
                .reverse()
                .map((h) => (
                  <button
                    className="history-question"
                    key={h.id}
                    onClick={async () => {
                      const result = await run("Opening practice history", () =>
                        api<Training>("/training/sessions/" + h.id),
                      );
                      if (result) setSession(result);
                    }}
                  >
                    <span>
                      <strong>{h.scenario}</strong>
                      <small>
                        {h.turns}/3 turns ·{" "}
                        {h.complete ? "Review coaching" : "Resume practice"}
                      </small>
                    </span>
                    <ArrowRight size={14} />
                  </button>
                ))
            ) : (
              <p className="muted">
                Your saved practice sessions will appear here.
              </p>
            )}
          </Panel>
          <AcademyKnowledge
            domainId={domain}
            renderSources={(ids) => <Sources ids={ids} />}
          />
          <Panel title="Shared product knowledge">
            <p className="muted">
              Practice and customer work use the same approved sources.
            </p>
            <Sources
              ids={kb
                .filter(
                  (d) =>
                    (d.domain_id || "synthetic-device-lifecycle") === domain,
                )
                .slice(0, 4)
                .map((d) => d.id)}
            />
          </Panel>
        </aside>
      </div>
    </>
  );
}
