"use client";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ChevronDown,
  Mic,
  PenLine,
  Plus,
  RefreshCw,
  Scissors,
  Search,
} from "lucide-react";
import { api } from "../api";
import { AudioObservations } from "../workflow-tools";
import type { Conversation, Segment } from "../types";
import { useWorkspace } from "./context";
import {
  Badge,
  DetailList,
  EvidenceLink,
  Modal,
  NextStep,
  Panel,
  pretty,
  time,
} from "./ui";
export function ConversationStage() {
  const {
    c,
    apply,
    run,
    busy,
    processing,
    review,
    setStage,
    highlight,
    setIntake,
  } = useWorkspace();
  const [observation, setObservation] = useState<
      Conversation["observations"][number] | null
    >(null),
    [observationText, setObservationText] = useState(""),
    [observationReason, setObservationReason] = useState("");
  const [search, setSearch] = useState(""),
    [editing, setEditing] = useState(false),
    [segments, setSegments] = useState<Segment[]>([]),
    [reason, setReason] = useState(""),
    [note, setNote] = useState(""),
    [split, setSplit] = useState<Segment | null>(null),
    [turn, setTurn] = useState(""),
    [turnRole, setTurnRole] = useState("customer");
  const player = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    setSegments(c?.segments || []);
    setEditing(false);
    setReason("");
    setSplit(null);
  }, [c?.id, c?.version]);
  if (!c) return null;
  const unassigned = c.segments.filter((s) => s.role === "unknown").length;
  const found = segments.filter((s) =>
    s.text.toLowerCase().includes(search.toLowerCase()),
  );
  const observations = c.observations.filter((o) => !o.dismissed),
    questions = observations.filter((o) =>
      ["question", "objection", "constraint"].includes(o.kind),
    );
  async function save() {
    if (!c) return;
    const result = await run("Saving transcript and restarting analysis", () =>
      api<Conversation>(
        `/conversations/${c.id}/transcript?background=true`,
        {
          version: c.version,
          segments,
          reason: reason + (note ? ": " + note : ""),
        },
        "Sales Representative",
        "PATCH",
      ),
    );
    if (result) apply(result);
  }
  async function addTurn() {
    if (!c) return;
    const result = await run("Adding the conversation turn", () =>
      api<Conversation>(`/conversations/${c.id}/turns`, {
        version: c.version,
        text: turn,
        role: turnRole,
        synthetic_consent: true,
      }),
    );
    if (result) {
      apply(result);
      setTurn("");
    }
  }
  return (
    <>
      {observation && (
        <Modal
          title="Review conversation observation"
          onClose={() => setObservation(null)}
        >
          <EvidenceLink items={observation.evidence} />
          <label>
            Observation wording
            <textarea
              value={observationText}
              onChange={(e) => setObservationText(e.target.value)}
            />
          </label>
          <label>
            Reason
            <input
              value={observationReason}
              onChange={(e) => setObservationReason(e.target.value)}
              placeholder="Explain your correction or dismissal"
            />
          </label>
          <div className="modal-footer">
            <button
              className="secondary"
              disabled={!!busy || !observationReason.trim()}
              onClick={async () => {
                if (
                  await review(
                    "observation",
                    observation.id,
                    { dismissed: true },
                    observationReason,
                  )
                )
                  setObservation(null);
              }}
            >
              Dismiss observation
            </button>
            <button
              className="primary"
              disabled={
                !!busy || !observationReason.trim() || !observationText.trim()
              }
              onClick={async () => {
                if (
                  await review(
                    "observation",
                    observation.id,
                    { description: observationText },
                    observationReason,
                  )
                )
                  setObservation(null);
              }}
            >
              Save correction
            </button>
          </div>
        </Modal>
      )}
      <div className="stage-heading">
        <div>
          <span className="eyebrow">01 / LISTEN & UNDERSTAND</span>
          <h1>The conversation, in context.</h1>
          <p>
            Review the words and speakers before turning them into commitments.
          </p>
        </div>
        <button
          className="secondary"
          disabled={!!busy || processing || !c.segments.length}
          onClick={() => review("analyse")}
        >
          <RefreshCw size={15} />
          Reanalyse
        </button>
      </div>
      <div className="conversation-layout">
        <div className="conversation-main">
          <Panel
            title="Conversation replay"
            action={
              <Badge tone={unassigned ? "amber" : "green"}>
                {unassigned
                  ? `${unassigned} unassigned turns`
                  : "Roles assigned"}
              </Badge>
            }
          >
            {c.audio_path ? (
              <div className="audio-player">
                <div className="inline">
                  <Mic size={16} />
                  <span>Original recording</span>
                  <small>{c.transcription_model}</small>
                </div>
                <audio
                  ref={player}
                  controls
                  src={`/api/conversations/${c.id}/recording`}
                />
              </div>
            ) : (
              <div className="transcript-source">
                <Mic size={17} />
                <span>
                  {c.source.includes("fixture")
                    ? "Example transcript · no speech model called"
                    : c.source.includes("brief")
                      ? "Customer brief · no speech model called"
                      : "Typed transcript · no speech model called"}
                </span>
              </div>
            )}
            <div className="transcript-toolbar">
              <label className="search-field">
                <Search size={16} />
                <input
                  aria-label="Search transcript"
                  placeholder="Find a word or phrase…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </label>
              <button
                className="secondary"
                disabled={!!busy || processing || !segments.length}
                onClick={() => setEditing(!editing)}
              >
                <PenLine size={14} />
                {editing ? "Cancel editing" : "Review transcript"}
              </button>
            </div>
            {unassigned > 0 && !editing && (
              <div className="note amber">
                <strong>Assign the speakers first.</strong>
                <p>
                  Short-clip transcription has no automatic speaker separation.
                  Review roles, or split a long segment into separate turns.
                </p>
              </div>
            )}
            {editing && (
              <div className="transcript-review">
                <div className="inline spread">
                  <strong>Speaker mapping</strong>
                  <label className="compact-label">
                    Apply to speaker
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        const [speaker, role] = e.target.value.split("|");
                        if (role)
                          setSegments(
                            segments.map((s) =>
                              s.speaker_id === speaker
                                ? { ...s, role: role as Segment["role"] }
                                : s,
                            ),
                          );
                      }}
                    >
                      <option value="">Choose a speaker & role</option>
                      {Array.from(
                        new Set(segments.map((s) => s.speaker_id)),
                      ).flatMap((speaker) =>
                        ["customer", "sales", "unknown"].map((role) => (
                          <option
                            key={speaker + role}
                            value={speaker + "|" + role}
                          >
                            {speaker} →{" "}
                            {role === "unknown" ? "Unassigned" : pretty(role)}
                          </option>
                        )),
                      )}
                    </select>
                  </label>
                </div>
                <p className="field-help">
                  Corrections preserve the original transcript and invalidate
                  previous reviews.
                </p>
              </div>
            )}
            <div className="transcript-feed">
              {found.length ? (
                found.map((s, i) => (
                  <article
                    id={"turn-" + s.id}
                    key={s.id}
                    className={`transcript-turn ${s.role} ${highlight === s.id ? "highlighted" : ""}`}
                  >
                    <div className="turn-avatar">
                      {s.role === "customer"
                        ? "C"
                        : s.role === "sales"
                          ? "S"
                          : "?"}
                    </div>
                    <div className="turn-content">
                      <header>
                        <strong>
                          {s.role === "unknown"
                            ? "Unassigned speaker"
                            : s.role === "customer"
                              ? "Customer"
                              : "Sales representative"}
                        </strong>
                        <span>
                          {s.start_ms === null
                            ? `Turn ${i + 1}`
                            : time(s.start_ms)}
                        </span>
                        {s.id.startsWith("turn-") && (
                          <Badge>Session note</Badge>
                        )}
                        {editing && (
                          <select
                            aria-label={`Role for turn ${i + 1}`}
                            value={s.role}
                            onChange={(e) =>
                              setSegments(
                                segments.map((x) =>
                                  x.id === s.id
                                    ? {
                                        ...x,
                                        role: e.target.value as Segment["role"],
                                      }
                                    : x,
                                ),
                              )
                            }
                          >
                            <option value="unknown">Unassigned</option>
                            <option value="customer">Customer</option>
                            <option value="sales">Sales</option>
                          </select>
                        )}
                      </header>
                      {editing ? (
                        <textarea
                          aria-label={`Transcript turn ${i + 1}`}
                          value={s.text}
                          onChange={(e) =>
                            setSegments(
                              segments.map((x) =>
                                x.id === s.id
                                  ? { ...x, text: e.target.value }
                                  : x,
                              ),
                            )
                          }
                        />
                      ) : (
                        <p>{s.text}</p>
                      )}
                      <div className="turn-actions">
                        {s.start_ms !== null && c.audio_path && (
                          <button
                            className="text-button"
                            onClick={() => {
                              if (player.current) {
                                player.current.currentTime = s.start_ms! / 1000;
                                void player.current.play().catch(() => {});
                              }
                            }}
                          >
                            Play from here
                          </button>
                        )}
                        <details>
                          <summary>Original wording</summary>
                          <p>{s.original_text || s.text}</p>
                          {s.parent_segment_id && (
                            <small>
                              Split from {s.parent_segment_id}; exact turn
                              timing is unknown.
                            </small>
                          )}
                        </details>
                        <button
                          className="text-button"
                          disabled={!!busy || processing}
                          onClick={() => setSplit(s)}
                        >
                          <Scissors size={12} />
                          Split into turns
                        </button>
                      </div>
                    </div>
                  </article>
                ))
              ) : (
                <p className="muted">
                  {segments.length
                    ? "No transcript turns match your search."
                    : "The transcript will appear here when processing finishes."}
                </p>
              )}
            </div>
            {editing && (
              <div className="review-footer">
                <label>
                  Reason for correction
                  <select
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  >
                    <option value="">Choose a reason</option>
                    <option>Assigned business roles</option>
                    <option>Corrected transcription wording</option>
                    <option>Corrected wording and speaker roles</option>
                  </select>
                </label>
                <label>
                  Review note (optional)
                  <input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Explain anything the next reviewer should know"
                  />
                </label>
                <button
                  className="primary"
                  disabled={
                    !!busy ||
                    processing ||
                    !reason ||
                    segments.some((s) => !s.text.trim())
                  }
                  onClick={save}
                >
                  Save & reanalyse <ArrowRight size={15} />
                </button>
              </div>
            )}
          </Panel>
          <details className="advanced-panel">
            <summary>
              <Plus size={16} />
              Add a conversation turn or session note
            </summary>
            <div className="advanced-body">
              <p className="muted">
                Add fictional customer or sales wording as the discussion
                develops. This regenerates the analysis and clears previous
                approvals.
              </p>
              <label>
                Speaker
                <select
                  value={turnRole}
                  onChange={(e) => setTurnRole(e.target.value)}
                >
                  <option value="customer">Customer</option>
                  <option value="sales">Sales representative</option>
                </select>
              </label>
              <label>
                New turn
                <textarea
                  rows={3}
                  value={turn}
                  onChange={(e) => setTurn(e.target.value)}
                  placeholder="What did the customer or salesperson say?"
                />
              </label>
              <button
                className="secondary"
                disabled={!!busy || processing || !turn.trim()}
                onClick={addTurn}
              >
                Add turn & analyse
              </button>
            </div>
          </details>
        </div>
        <aside className="conversation-sidebar">
          <Panel title="Customer intent" eyebrow="WHAT MATTERS TO THEM">
            {c.requirements
              .filter((r) => !r.superseded_by?.length)
              .slice(0, 5)
              .map((r) => (
                <div className="intent-item" key={r.id}>
                  <div className="inline spread">
                    <strong>{r.title}</strong>
                    <Badge
                      tone={
                        r.information_status === "explicit" ? "green" : "amber"
                      }
                    >
                      {r.information_status}
                    </Badge>
                  </div>
                  <p>{r.description}</p>
                  <EvidenceLink items={r.evidence} />
                </div>
              ))}
            {!c.requirements.length && (
              <p className="muted">
                {unassigned
                  ? "Assign customer and sales roles, then run analysis."
                  : "Extracted needs will appear after analysis."}
              </p>
            )}
            {c.requirements.length > 0 && (
              <button
                className="text-button"
                onClick={() => setStage("requirements")}
              >
                Review all requirements <ArrowRight size={14} />
              </button>
            )}
          </Panel>
          <Panel title="Questions & concerns">
            {questions.length ? (
              questions.slice(0, 4).map((o) => (
                <div className="intent-item" key={o.id}>
                  <Badge>{pretty(o.kind)}</Badge>
                  <p>{o.description}</p>
                  <EvidenceLink items={o.evidence} />
                  <button
                    className="text-button"
                    disabled={!!busy || processing}
                    onClick={() => {
                      setObservation(o);
                      setObservationText(o.description);
                      setObservationReason("");
                    }}
                  >
                    Review observation
                  </button>
                </div>
              ))
            ) : (
              <p className="muted">
                Questions and concerns are shown when grounded in customer
                wording.
              </p>
            )}
          </Panel>
          <details className="advanced-panel">
            <summary>
              <ChevronDown size={16} />
              Audio observations
            </summary>
            <div className="advanced-body">
              {c.audio_path ? (
                <AudioObservations cid={c.id} />
              ) : (
                <>
                  <p>
                    Upload a recording to measure energy and low-energy spans.
                    No audio measurements are inferred from typed text.
                  </p>
                  <button
                    className="text-button"
                    onClick={() => setIntake(true)}
                  >
                    Add a recording
                  </button>
                </>
              )}
            </div>
          </details>
        </aside>
      </div>
      <details className="advanced-panel">
        <summary>Processing details & actual providers</summary>
        <div className="advanced-body">
          <p className="muted small">
            Speech: {c.transcription_model}. Wording matches complement model
            extraction; interpretations remain reviewable.
          </p>
          {c.node_runs.map((n, i) => (
            <div className="provider-row" key={i}>
              <span>{pretty(n.node)}</span>
              <strong>{n.provider}</strong>
              <small>
                {n.status} · {(n.duration_ms / 1000).toFixed(1)} seconds
              </small>
            </div>
          ))}
        </div>
      </details>
      <NextStep
        stage="sales"
        label="Use the reviewed context to prepare a grounded answer and a better follow-up question."
      />
      {split && <SplitDialog segment={split} onClose={() => setSplit(null)} />}
    </>
  );
}
function SplitDialog({
  segment,
  onClose,
}: {
  segment: Segment;
  onClose: () => void;
}) {
  const { c, run, apply, busy } = useWorkspace();
  const [parts, setParts] = useState([
      { role: "customer", text: segment.text },
      { role: "sales", text: "" },
    ]),
    [reason, setReason] = useState("");
  async function save() {
    if (!c) return;
    const result = await run("Splitting transcript and analysing roles", () =>
      api<Conversation>(`/conversations/${c.id}/split-transcript`, {
        version: c.version,
        segment_id: segment.id,
        parts,
        reason,
      }),
    );
    if (result) {
      apply(result);
      onClose();
    }
  }
  return (
    <Modal title="Split a transcript segment" onClose={onClose} wide>
      <p className="muted">
        Move the original words into turns in the same order. Assign roles after
        listening. The system will not invent timestamps for these turns.
      </p>
      <details>
        <summary>Original segment</summary>
        <blockquote>{segment.text}</blockquote>
      </details>
      {parts.map((part, i) => (
        <div className="split-part" key={i}>
          <label>
            Turn {i + 1} speaker
            <select
              value={part.role}
              onChange={(e) =>
                setParts(
                  parts.map((p, n) =>
                    i === n ? { ...p, role: e.target.value } : p,
                  ),
                )
              }
            >
              <option value="customer">Customer</option>
              <option value="sales">Sales</option>
              <option value="unknown">Unassigned</option>
            </select>
          </label>
          <label>
            Exact wording
            <textarea
              rows={3}
              value={part.text}
              onChange={(e) =>
                setParts(
                  parts.map((p, n) =>
                    i === n ? { ...p, text: e.target.value } : p,
                  ),
                )
              }
            />
          </label>
        </div>
      ))}
      <button
        className="text-button"
        disabled={parts.length >= 30}
        onClick={() => setParts([...parts, { role: "customer", text: "" }])}
      >
        Add another turn
      </button>
      <label>
        Review reason
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="How did you identify the turn boundaries?"
        />
      </label>
      <div className="modal-footer">
        <button className="secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          className="primary"
          disabled={
            !!busy ||
            reason.trim().length < 5 ||
            parts.some((p) => !p.text.trim())
          }
          onClick={save}
        >
          Save turns & analyse
        </button>
      </div>
    </Modal>
  );
}
