"use client";
import { useEffect, useState } from "react";
import { ArrowRight, Check, Copy, Send, Sparkles } from "lucide-react";
import { api } from "../api";
import type { CopilotSuggestion } from "../types";
import { useWorkspace } from "./context";
import {
  Badge,
  DetailList,
  EvidenceLink,
  NextStep,
  Panel,
  Sources,
  pretty,
} from "./ui";
export function SalesStage() {
  const { c, ask, busy, processing, run, review, notify, providers } =
    useWorkspace();
  const [question, setQuestion] = useState(""),
    [language, setLanguage] = useState("English"),
    [answer, setAnswer] = useState<CopilotSuggestion | null>(null),
    [pitch, setPitch] = useState(""),
    [audience, setAudience] = useState("business"),
    [pitchProvider, setPitchProvider] = useState(
      "approved-catalogue-templates",
    ),
    [useModel, setUseModel] = useState(true),
    [rationale, setRationale] = useState("");
  useEffect(() => {
    setPitch(c?.sales.pitch || "");
    setAnswer(c?.copilot_history?.slice(-1)[0] || null);
    setQuestion("");
    setRationale("");
  }, [c?.id]);
  useEffect(() => {
    setPitch(c?.sales.pitch || "");
  }, [c?.sales.pitch]);
  if (!c) return null;
  const fit = c.sales.fit_reasons || [],
    gaps = c.sales.limitations || [];
  async function send(event?: React.FormEvent, text = question) {
    event?.preventDefault();
    if (!text.trim()) return;
    const result = await ask(text, language);
    if (result) setAnswer(result);
  }
  async function adapt() {
    if (!c) return;
    const result = await run("Adapting the pitch to this customer", () =>
      api<{ pitch: string; provider: string }>(`/conversations/${c.id}/pitch`, {
        language,
        familiarity: audience,
        use_model: useModel,
      }),
    );
    if (result) {
      setPitch(result.pitch);
      setPitchProvider(result.provider);
      setRationale("");
    }
  }
  async function copy(text: string) {
    const result = await run("Copying suggested wording", async () => {
      await navigator.clipboard.writeText(text);
      return true;
    });
    if (result)
      notify("Copied. Review the wording and conditions before sharing.");
  }
  const questions = c.observations.filter(
    (o) => o.kind === "question" && !o.dismissed,
  );
  return (
    <>
      <div className="stage-heading">
        <div>
          <span className="eyebrow">02 / SUPPORT THE REPRESENTATIVE</span>
          <h1>The right context. A better answer.</h1>
          <p>
            Ask a product question, inspect its sources and prepare the next
            conversation.
          </p>
        </div>
        <Badge tone="green">
          <Sparkles size={12} />
          {providers?.reasoning.model || "Approved product knowledge"}
        </Badge>
      </div>
      <div className="sales-layout">
        <div className="sales-main">
          <Panel
            title="Ask Sales Copilot"
            eyebrow="CUSTOMER QUESTION → GROUNDED SUGGESTION"
            action={
              <label className="compact-label">
                Answer language
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option>English</option>
                  <option>Hindi</option>
                  <option>Hinglish</option>
                </select>
              </label>
            }
          >
            <form className="copilot-composer" onSubmit={send}>
              <textarea
                rows={3}
                aria-label="Customer question for Sales Copilot"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={
                  c.domain_id === "marketplace"
                    ? "How do we recommend a new product without clicks or purchase history?"
                    : "Can repair partners access device history without seeing owner details?"
                }
              />
              <div className="inline spread">
                <span className="small muted">
                  Uses this conversation and its approved product sources.
                </span>
                <button
                  className="primary"
                  disabled={!!busy || processing || !question.trim()}
                >
                  <Send size={15} />
                  Find an answer
                </button>
              </div>
            </form>
            {!answer && (
              <div className="suggestion-prompts">
                {(questions.length
                  ? questions
                      .slice(0, 2)
                      .map((q) => q.evidence[0]?.quote)
                      .filter(Boolean)
                  : [
                      c.domain_id === "marketplace"
                        ? "How does the cold-start approach work without historical interaction data?"
                        : "What conditions apply to ERP integration?",
                    ]
                ).map((q) => (
                  <button
                    className="suggestion-chip"
                    key={q}
                    disabled={!!busy || processing}
                    onClick={() => {
                      setQuestion(q);
                      void send(undefined, q);
                    }}
                  >
                    {q}
                    <ArrowRight size={13} />
                  </button>
                ))}
              </div>
            )}
            {answer && (
              <article className="copilot-answer">
                <div className="inline spread">
                  <div className="inline">
                    <span className="assistant-symbol">
                      <Sparkles size={17} />
                    </span>
                    <strong>Suggested answer</strong>
                    <Badge
                      tone={
                        answer.status === "supported"
                          ? "green"
                          : answer.status === "unsupported"
                            ? "red"
                            : "amber"
                      }
                    >
                      {pretty(answer.status)}
                    </Badge>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => copy(answer.answer)}
                  >
                    <Copy size={14} />
                    Copy
                  </button>
                </div>
                <p className="question-context">{answer.question}</p>
                <div className="answer-text">{answer.answer}</div>
                <Sources ids={answer.sources || []} />
                <div className="next-question">
                  <span className="eyebrow">ASK NEXT</span>
                  <p>{answer.next_question}</p>
                </div>
                {answer.objection_response && (
                  <details>
                    <summary>Acknowledge the concern</summary>
                    <p>{answer.objection_response}</p>
                  </details>
                )}
                {answer.escalation_required && (
                  <div className="note amber">
                    <strong>Bring a specialist into the decision</strong>
                    <p>{answer.escalation_reason}</p>
                  </div>
                )}
                {!!answer.conditions?.length && (
                  <details>
                    <summary>Documented conditions</summary>
                    {answer.conditions.map((text, i) => (
                      <p key={i}>{text}</p>
                    ))}
                  </details>
                )}
                <p className="provenance">
                  {answer.model_used
                    ? "AI-generated suggestion"
                    : "Source-based retrieval"}{" "}
                  · {answer.provider} · review before use
                </p>
              </article>
            )}
            {!!c.copilot_history?.length && (
              <details className="answer-history">
                <summary>
                  Earlier questions in this conversation (
                  {c.copilot_history.length})
                </summary>
                {c.copilot_history
                  .slice()
                  .reverse()
                  .map((a, i) => (
                    <button
                      key={i}
                      className="history-question"
                      onClick={() => setAnswer(a)}
                    >
                      {a.question}
                      <ArrowRight size={14} />
                    </button>
                  ))}
              </details>
            )}
          </Panel>
          <Panel title="Prepare your pitch" eyebrow="ADAPT THE WORDING">
            <div className="pitch-toolbar">
              <label>
                Audience
                <select
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                >
                  <option value="business">Business audience</option>
                  <option value="technical">Technical audience</option>
                </select>
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={useModel}
                  onChange={(e) => setUseModel(e.target.checked)}
                />
                Use AI to tailor the pitch
              </label>
              <button
                className="secondary"
                disabled={!!busy || processing || !c.requirements.length}
                onClick={adapt}
              >
                <Sparkles size={15} />
                Adapt pitch
              </button>
            </div>
            <label className="sr-only" htmlFor="sales-pitch">
              Editable sales pitch
            </label>
            <textarea
              id="sales-pitch"
              rows={6}
              value={pitch}
              onChange={(e) => setPitch(e.target.value)}
              placeholder="Analyse the conversation to build a pitch grounded in the customer's needs."
            />
            <div className="inline spread">
              <span className="provenance">
                {pitchProvider.includes("/")
                  ? "AI-tailored suggestion"
                  : "Source-based starting point"}
              </span>
              <button
                className="text-button"
                disabled={!pitch}
                onClick={() => copy(pitch)}
              >
                <Copy size={14} />
                Copy pitch
              </button>
            </div>
            <div className="pitch-review">
              <label>
                Review basis
                <select
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                >
                  <option value="">Choose after checking the pitch</option>
                  <option>
                    Matches the customer need and documented conditions
                  </option>
                  <option>
                    Reviewed and edited for the customer's language and context
                  </option>
                </select>
              </label>
              <button
                className="secondary"
                disabled={!!busy || processing || !pitch.trim() || !rationale}
                onClick={() =>
                  review(
                    "sales",
                    undefined,
                    { pitch, pitch_reviewed: true },
                    rationale,
                  )
                }
              >
                <Check size={15} />
                {c.sales.pitch_reviewed && pitch === c.sales.pitch
                  ? "Pitch reviewed"
                  : "Mark pitch reviewed"}
              </button>
            </div>
            <Sources ids={c.sales.sources || []} />
          </Panel>
        </div>
        <aside className="sales-sidebar">
          <Panel title="Product fit" eyebrow="EXPLAIN THE RECOMMENDATION">
            <h3 className="recommendation-title">
              {c.sales.product_name || "More context needed"}
            </h3>
            {fit.length ? (
              fit.map((f, i) => {
                const r = c.requirements.find((r) => r.id === f.need_id);
                return (
                  <div className="fit-reason" key={i}>
                    <span className="fit-check">
                      <Check size={16} />
                    </span>
                    <div>
                      <strong>{f.reason}</strong>
                      {r && <EvidenceLink items={r.evidence} />}
                      <Sources ids={f.sources} />
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="muted">
                Confirm the customer need and review available documentation
                before recommending a configuration.
              </p>
            )}
            {!!gaps.length && (
              <details>
                <summary>{gaps.length} conditions or gaps to review</summary>
                <ul>
                  {gaps.map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                </ul>
              </details>
            )}
          </Panel>
          <Panel title="Move discovery forward">
            <div className="next-question">
              <span className="eyebrow">NEXT-BEST QUESTION</span>
              <p>
                {c.sales.next_question ||
                  "Which customer workflow should we clarify first?"}
              </p>
            </div>
            <p className="muted">{c.sales.objection_handling}</p>
            {c.sales.escalation_required && (
              <div className="note amber">
                <strong>Technical review recommended</strong>
                <p>{c.sales.escalation_reason}</p>
              </div>
            )}
          </Panel>
          <Panel title="What the customer said">
            {c.requirements.slice(0, 3).map((r) => (
              <div className="intent-item" key={r.id}>
                <strong>{r.title}</strong>
                <p>{r.description}</p>
                <Badge
                  tone={r.information_status === "explicit" ? "green" : "amber"}
                >
                  {r.information_status}
                </Badge>
                <EvidenceLink items={r.evidence} />
              </div>
            ))}
          </Panel>
        </aside>
      </div>
      <NextStep
        stage="requirements"
        label="Turn the customer's needs into reviewed scope and acceptance checks."
      />
    </>
  );
}
