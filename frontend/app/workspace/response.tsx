"use client";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Check,
  Copy,
  Download,
  Save,
  ShieldCheck,
  Sparkles,
  Volume2,
} from "lucide-react";
import { api } from "../api";
import type { Conversation, Stage } from "../types";
import { useWorkspace } from "./context";
import { Badge, Panel, Sources, pretty } from "./ui";
import { IntegrityReview } from "./review";
export function ResponseStage() {
  const {
    c,
    journey: j,
    busy,
    processing,
    review,
    run,
    apply,
    setStage,
    providers,
    notify,
  } = useWorkspace();
  const [language, setLanguage] = useState("English"),
    [detail, setDetail] = useState("short"),
    [useAI, setUseAI] = useState(true),
    [text, setText] = useState("");
  useEffect(() => {
    setText(c?.response?.text || "");
    if (c?.response) setLanguage(c.response.language);
  }, [c?.id, c?.response?.text]);
  if (!c) return null;
  const dirty = !!c.response && text !== c.response.text;
  const current = j?.version === c.version;
  const active = c.requirements.filter(
    (r) =>
      !["deferred", "rejected"].includes(r.pm_status) &&
      !r.superseded_by?.length,
  );
  const accepted =
    active.length > 0 && active.every((r) => r.pm_status === "accepted");
  const engineering =
    accepted &&
    active.every(
      (r) =>
        c.assessments.find((a) => a.requirement_id === r.id)
          ?.reviewer_status === "approved",
    );
  const high = c.findings.filter(
    (f) =>
      f.severity === "high" &&
      !["resolved", "dismissed"].includes(f.reviewer_status),
  );
  async function speech() {
    if (!c) return;
    const next = await run(
      "Generating the approved response with Gnani Timbre",
      () =>
        api<Conversation>(
          `/conversations/${c.id}/audio`,
          {},
          "Sales Representative",
        ),
    );
    if (next) apply(next);
  }
  async function copy() {
    const result = await run("Copying the reviewed response", async () => {
      await navigator.clipboard.writeText(text);
      return true;
    });
    if (result) notify("Response copied.");
  }
  const go = (stage: Stage) => {
    setStage(stage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return (
    <>
      <div className="stage-heading">
        <div>
          <span className="eyebrow">05 / CLOSE THE LOOP</span>
          <h1>A clear answer back to the customer.</h1>
          <p>
            Keep the reviewed scope, dependencies and uncertainty in the final
            explanation.
          </p>
        </div>
        <Badge tone={c.response?.approved ? "green" : "amber"}>
          {c.response?.approved
            ? "Response approved"
            : c.response
              ? "Draft · needs review"
              : "Awaiting reviewed scope"}
        </Badge>
      </div>
      <div className="response-layout">
        <div>
          <Panel
            title="Customer-facing explanation"
            eyebrow="REVIEWED DECISIONS → PLAIN LANGUAGE"
          >
            <div className="response-options">
              <label>
                Language
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option>English</option>
                  <option>Hindi</option>
                  <option>Hinglish</option>
                </select>
              </label>
              <label>
                Detail
                <select
                  value={detail}
                  onChange={(e) => setDetail(e.target.value)}
                >
                  <option value="short">Concise explanation</option>
                  <option value="detailed">
                    Detailed with acceptance checks
                  </option>
                </select>
              </label>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={useAI}
                onChange={(e) => setUseAI(e.target.checked)}
              />
              <span>
                Use AI to turn reviewed decisions into customer language
              </span>
            </label>
            <button
              className="secondary"
              disabled={!!busy || processing || !current || !j?.can_draft}
              onClick={() =>
                review("draft", undefined, {
                  language,
                  detail,
                  model_draft: useAI && !!providers?.reasoning.configured,
                })
              }
            >
              <Sparkles size={16} />
              {c.response ? "Regenerate draft" : "Generate explanation"}
            </button>
            {!j?.can_draft && (
              <div className="note amber">
                <strong>Complete the review steps first.</strong>
                <p>
                  {!accepted
                    ? "Review and accept active scope in Requirements."
                    : !engineering
                      ? "Approve the active technical assessments in Engineering."
                      : high.length
                        ? "Resolve or dismiss high-priority intent findings below."
                        : "Review the conversation and its speaker roles."}
                </p>
                <button
                  className="text-button"
                  onClick={() => {
                    if (accepted && engineering && high.length) {
                      document.getElementById("intent-review")?.scrollIntoView({
                        behavior: "smooth",
                        block: "start",
                      });
                    } else
                      go(
                        !accepted
                          ? "requirements"
                          : !engineering
                            ? "engineering"
                            : "conversation",
                      );
                  }}
                >
                  Open the required step <ArrowRight size={14} />
                </button>
              </div>
            )}
            {c.response ? (
              <>
                <label className="response-editor-label">
                  Review and edit the explanation
                  <textarea
                    aria-label="Customer response wording"
                    rows={13}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                </label>
                <div className="inline spread">
                  <span className="provenance">
                    Drafted by{" "}
                    {c.response.generation_provider ||
                      "approved product sources"}
                  </span>
                  <button className="text-button" onClick={copy}>
                    <Copy size={14} />
                    Copy
                  </button>
                </div>
                <Sources ids={c.response.sources} />
                <div className="response-review-actions">
                  <button
                    className="secondary"
                    disabled={!!busy || processing || !dirty || !text.trim()}
                    onClick={() =>
                      review(
                        "response",
                        undefined,
                        { text, approved: false },
                        "Saved edited wording for intent review.",
                      )
                    }
                  >
                    <Save size={15} />
                    Save changes
                  </button>
                  <button
                    className="secondary"
                    disabled={
                      !!busy ||
                      processing ||
                      dirty ||
                      !providers?.reasoning.configured
                    }
                    onClick={() => review("semantic_audit")}
                  >
                    <ShieldCheck size={16} />
                    {j?.audit_current
                      ? "Recheck intent"
                      : "Check saved response"}
                  </button>
                  <button
                    className="primary"
                    disabled={
                      !!busy ||
                      processing ||
                      dirty ||
                      !current ||
                      !j?.can_approve ||
                      c.response.approved
                    }
                    onClick={() =>
                      review(
                        "response",
                        undefined,
                        { text, approved: true },
                        "Reviewed the exact response and its documented conditions.",
                      )
                    }
                  >
                    <Check size={16} />
                    {c.response.approved ? "Approved" : "Approve response"}
                  </button>
                </div>
                <p className="field-help">
                  {dirty
                    ? "Save your edits before checking intent. An edited draft needs a fresh check and approval."
                    : !j?.audit_current && j?.model_audit_required
                      ? "Run the AI intent check on this exact saved wording, then review any findings below."
                      : "Approval applies to the exact saved wording. Later edits clear approval and generated audio."}
                </p>
              </>
            ) : (
              <div className="response-placeholder">
                <Sparkles size={30} />
                <h3>Your reviewed explanation will appear here.</h3>
                <p>
                  Start with accepted requirements and approved engineering
                  decisions. The response will retain conditions and open
                  questions.
                </p>
              </div>
            )}
          </Panel>
          <div id="intent-review">
            <IntegrityReview />
          </div>
        </div>
        <aside>
          <Panel title="Review readiness" eyebrow="A CLEAR PATH TO APPROVAL">
            <div className="readiness-item">
              <span className={accepted ? "ready-check" : "pending-check"}>
                {accepted ? <Check size={15} /> : "1"}
              </span>
              <div>
                <strong>Customer scope reviewed</strong>
                <p>
                  {active.filter((r) => r.pm_status === "accepted").length}/
                  {active.length} active requirements accepted
                </p>
              </div>
              <button
                className="text-button"
                onClick={() => go("requirements")}
              >
                Open
              </button>
            </div>
            <div className="readiness-item">
              <span className={engineering ? "ready-check" : "pending-check"}>
                {engineering ? <Check size={15} /> : "2"}
              </span>
              <div>
                <strong>Technical decisions reviewed</strong>
                <p>Conditions and unknowns remain visible</p>
              </div>
              <button className="text-button" onClick={() => go("engineering")}>
                Open
              </button>
            </div>
            <div className="readiness-item">
              <span className={!high.length ? "ready-check" : "pending-check"}>
                {!high.length ? <Check size={15} /> : "3"}
              </span>
              <div>
                <strong>Material intent issues resolved</strong>
                <p>{high.length} high-priority findings remain</p>
              </div>
            </div>
            <div className="readiness-item">
              <span
                className={j?.audit_current ? "ready-check" : "pending-check"}
              >
                {j?.audit_current ? <Check size={15} /> : "4"}
              </span>
              <div>
                <strong>Exact response checked</strong>
                <p>
                  {j?.audit_current
                    ? "Semantic comparison is current"
                    : "Save the draft, then check intent"}
                </p>
              </div>
            </div>
            <div className="readiness-item">
              <span
                className={
                  c.response?.approved ? "ready-check" : "pending-check"
                }
              >
                {c.response?.approved ? <Check size={15} /> : "5"}
              </span>
              <div>
                <strong>Human approval recorded</strong>
                <p>
                  {c.response?.approved
                    ? "Approved for speech generation"
                    : "Review the wording before approval"}
                </p>
              </div>
            </div>
          </Panel>
          <Panel title="Let the customer hear it" eyebrow="GNANI TIMBRE">
            <div className="speech-illustration">
              <Volume2 size={32} />
              <div className="small-wave" aria-hidden="true">
                {[8, 19, 31, 22, 13, 26, 38, 18, 11].map((height, i) => (
                  <i key={i} style={{ height }} />
                ))}
              </div>
            </div>
            <p className="muted">
              Generate speech from the exact approved response.
            </p>
            <p className="provenance">
              {providers?.tts.model} · {providers?.tts.voice}
            </p>
            <button
              className="primary full"
              disabled={
                !!busy ||
                processing ||
                dirty ||
                !current ||
                !j?.can_generate_audio ||
                !providers?.tts.configured
              }
              onClick={speech}
            >
              <Volume2 size={16} />
              {c.response?.audio_path
                ? "Regenerate speech"
                : "Generate reviewed speech"}
            </button>
            {!providers?.tts.configured && (
              <p className="field-help">
                Configure the Gnani speech key on the server to enable speech.
              </p>
            )}
            {c.response?.audio_path && (
              <>
                <audio
                  controls
                  src={`/api/conversations/${c.id}/audio?version=${c.version}`}
                />
                <a
                  className="text-button"
                  href={`/api/conversations/${c.id}/audio?version=${c.version}`}
                  download="voicebridge-reviewed-response.wav"
                >
                  <Download size={14} />
                  Download audio
                </a>
              </>
            )}
          </Panel>
          <Panel title="Handoff packet">
            <p className="muted">
              Export the requirements, customer evidence and engineering
              decisions with their review status.
            </p>
            <div className="stack">
              <a
                className="secondary"
                href={`/api/conversations/${c.id}/handoff?format=markdown`}
                download
              >
                <Download size={15} />
                Readable handoff
              </a>
              <a
                className="text-button"
                href={`/api/conversations/${c.id}/handoff`}
                download
              >
                Download structured JSON
              </a>
            </div>
          </Panel>
        </aside>
      </div>
    </>
  );
}
