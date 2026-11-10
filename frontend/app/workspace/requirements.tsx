"use client";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Check,
  ClipboardList,
  Download,
  PenLine,
  Search,
} from "lucide-react";
import { RequirementOperations } from "../requirement-operations";
import { RequirementThemes } from "../workflow-tools";
import { EngineeringEditor } from "../engineering-editor";
import type { Requirement } from "../types";
import { useWorkspace } from "./context";
import {
  Badge,
  DetailList,
  EmptyState,
  EvidenceLink,
  NextStep,
  Panel,
  Sources,
  pretty,
} from "./ui";
import { IntegrityReview } from "./review";
export function RequirementsStage({
  engineering = false,
}: {
  engineering?: boolean;
}) {
  const { c, busy, processing, review, setStage } = useWorkspace();
  const [selected, setSelected] = useState(""),
    [filter, setFilter] = useState("all"),
    [query, setQuery] = useState("");
  useEffect(() => {
    if (c && !c.requirements.some((r) => r.id === selected))
      setSelected(
        c.requirements.find((r) => !r.superseded_by?.length)?.id || "",
      );
  }, [c?.id, c?.requirements, selected]);
  if (!c) return null;
  const active = c.requirements.filter((r) => !r.superseded_by?.length);
  const list = active.filter(
    (r) =>
      (filter === "all" || filter === "inferred"
        ? filter !== "inferred" || r.information_status !== "explicit"
        : r.pm_status === filter) &&
      `${r.title} ${r.description}`.toLowerCase().includes(query.toLowerCase()),
  );
  const req = list.find((r) => r.id === selected) || list[0];
  const accepted = active.filter((r) => r.pm_status === "accepted").length;
  return (
    <>
      <div className="stage-heading">
        <div>
          <span className="eyebrow">
            {engineering
              ? "04 / REVIEW TECHNICAL FEASIBILITY"
              : "03 / CLARIFY THE SCOPE"}
          </span>
          <h1>
            {engineering
              ? "What can we commit to?"
              : "Customer language. Clear requirements."}
          </h1>
          <p>
            {engineering
              ? "Check the documented support, dependencies and unknowns for each accepted need."
              : "Review each need with its original evidence before handing it to engineering."}
          </p>
        </div>
        <a
          className="secondary"
          href={`/api/conversations/${c.id}/handoff?format=markdown`}
          download
        >
          <Download size={15} />
          Export handoff
        </a>
      </div>
      {!active.length ? (
        <EmptyState
          title="No requirements to review yet"
          action={
            <button
              className="primary"
              onClick={() => setStage("conversation")}
            >
              Review the conversation <ArrowRight size={15} />
            </button>
          }
        >
          Assign speaker roles and analyse the transcript to build a
          source-linked backlog.
        </EmptyState>
      ) : (
        <>
          <div className="review-summary">
            <div>
              <strong>
                {accepted}/{active.length}
              </strong>
              <span>scope accepted</span>
            </div>
            <div>
              <strong>
                {
                  c.assessments.filter(
                    (a) =>
                      a.reviewer_status === "approved" &&
                      active.some(
                        (r) =>
                          r.id === a.requirement_id &&
                          r.pm_status === "accepted",
                      ),
                  ).length
                }
              </strong>
              <span>technical assessments approved</span>
            </div>
            <div>
              <strong>
                {
                  active.filter((r) => r.information_status !== "explicit")
                    .length
                }
              </strong>
              <span>need customer confirmation</span>
            </div>
            <Badge>
              {engineering
                ? "Technical reviewer workspace"
                : "Product manager workspace"}
            </Badge>
          </div>
          <div className="requirements-layout">
            <aside className="requirement-list">
              <div className="requirement-search">
                <label className="search-field">
                  <Search size={15} />
                  <input
                    aria-label="Search requirements"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Find a requirement…"
                  />
                </label>
                <select
                  aria-label="Filter requirements"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All active requirements</option>
                  <option value="pending">Awaiting review</option>
                  <option value="inferred">Inferred or assumed</option>
                  <option value="accepted">Accepted</option>
                  <option value="needs_clarification">
                    Needs clarification
                  </option>
                  <option value="deferred">Deferred</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              {list.length ? (
                list.map((r) => {
                  const a = c.assessments.find(
                    (a) => a.requirement_id === r.id,
                  );
                  return (
                    <button
                      key={r.id}
                      onClick={() => setSelected(r.id)}
                      className={
                        "requirement-row " +
                        (req?.id === r.id ? "selected" : "")
                      }
                    >
                      <span className="inline spread">
                        <span className="priority">{r.priority}</span>
                        <Badge
                          tone={
                            r.pm_status === "accepted"
                              ? "green"
                              : r.pm_status === "pending"
                                ? "amber"
                                : ""
                          }
                        >
                          {pretty(
                            engineering
                              ? a?.reviewer_status || "pending"
                              : r.pm_status,
                          )}
                        </Badge>
                      </span>
                      <strong className="requirement-list-title">
                        {r.title}
                      </strong>
                      <span className="small muted">
                        {engineering
                          ? pretty(a?.status || "unknown")
                          : pretty(r.information_status)}{" "}
                        · {r.evidence.length} evidence{" "}
                        {r.evidence.length === 1 ? "link" : "links"}
                      </span>
                    </button>
                  );
                })
              ) : (
                <p className="muted inset">
                  No requirements match this filter.
                </p>
              )}
            </aside>
            <div className="requirement-detail">
              {req &&
                (engineering ? (
                  <TechnicalDetail
                    key={req.id + "-" + c.version}
                    requirement={req}
                  />
                ) : (
                  <ScopeDetail
                    key={req.id + "-" + c.version}
                    requirement={req}
                  />
                ))}
            </div>
          </div>
          {!engineering && (
            <details className="advanced-panel">
              <summary>
                <ClipboardList size={16} />
                Organize scope: themes, overlaps, merge & split
              </summary>
              <div className="advanced-body">
                <RequirementThemes requirements={c.requirements} />
                <RequirementOperations
                  requirements={c.requirements}
                  version={c.version}
                  disabled={!!busy || processing}
                  onSave={(action, changes, reason) =>
                    void review(action, undefined, changes, reason)
                  }
                />
              </div>
            </details>
          )}
          {engineering && <IntegrityReview />}
          <NextStep
            stage={engineering ? "response" : "engineering"}
            label={
              engineering
                ? "Review intent integrity, then prepare the customer-facing explanation."
                : "Hand accepted scope to engineering with evidence and testable checks attached."
            }
          />
        </>
      )}
    </>
  );
}
function ScopeDetail({ requirement: r }: { requirement: Requirement }) {
  const { busy, processing, review } = useWorkspace();
  const [edit, setEdit] = useState(false),
    [title, setTitle] = useState(r.title),
    [description, setDescription] = useState(r.description),
    [criteria, setCriteria] = useState(r.acceptance_criteria.join("\n")),
    [story, setStory] = useState(r.user_story),
    [priority, setPriority] = useState(r.priority),
    [notes, setNotes] = useState(r.notes),
    [confirmed, setConfirmed] = useState(r.information_status === "explicit"),
    [reason, setReason] = useState("");
  const valid =
    !!reason &&
    !!title.trim() &&
    !!description.trim() &&
    criteria.split("\n").filter((v) => v.trim()).length > 0;
  async function save(status: string) {
    await review(
      "pm",
      r.id,
      {
        title,
        description,
        user_story: story,
        acceptance_criteria: criteria
          .split("\n")
          .map((v) => v.trim())
          .filter(Boolean),
        priority,
        notes,
        pm_status: status,
        information_status: confirmed ? "explicit" : r.information_status,
      },
      reason,
    );
  }
  return (
    <Panel
      title={r.title}
      eyebrow={r.id}
      action={
        <button className="text-button" onClick={() => setEdit(!edit)}>
          <PenLine size={14} />
          {edit ? "Preview scope" : "Edit scope"}
        </button>
      }
    >
      <div className="inline">
        <Badge tone={r.information_status === "explicit" ? "green" : "amber"}>
          {pretty(r.information_status)}
        </Badge>
        <Badge>
          {r.extraction_origin === "catalogue_coverage"
            ? "Suggested catalogue mapping"
            : r.extraction_origin === "model"
              ? "AI extracted"
              : "Source-linked scope"}
        </Badge>
        <Badge>{pretty(r.category)}</Badge>
      </div>
      <div className="requirement-evidence">
        <span className="eyebrow">ORIGINAL CUSTOMER EVIDENCE</span>
        {r.evidence.slice(0, 2).map((ev, i) => (
          <blockquote key={i}>“{ev.quote}”</blockquote>
        ))}
        <EvidenceLink items={r.evidence} label="Inspect source wording" />
      </div>
      {edit ? (
        <>
          <label>
            Requirement title
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Requested behavior
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <label>
            Proposed acceptance checks (one per line)
            <textarea
              rows={5}
              value={criteria}
              onChange={(e) => setCriteria(e.target.value)}
            />
          </label>
          <label>
            User story
            <textarea
              rows={3}
              value={story}
              onChange={(e) => setStory(e.target.value)}
            />
          </label>
        </>
      ) : (
        <>
          <p className="requirement-description">{description}</p>
          <DetailList
            title="Proposed acceptance checks"
            items={r.acceptance_criteria}
          />
          <details>
            <summary>User story</summary>
            <p>{r.user_story}</p>
          </details>
        </>
      )}
      <DetailList title="Constraints to preserve" items={r.constraints} />
      <DetailList title="Clarification needed" items={r.open_questions} />
      <div className="review-form">
        <div className="form-grid">
          <label>
            Priority
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="P0">P0 · Critical</option>
              <option value="P1">P1 · Important</option>
              <option value="P2">P2 · Later</option>
            </select>
          </label>
          <label>
            Decision rationale
            <select value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="">Choose after reviewing the evidence</option>
              <option>
                Matches the customer's stated need and constraints
              </option>
              <option>Confirmed the inferred need with the customer</option>
              <option>Needs more customer information</option>
              <option>Deferred from the current scope</option>
              <option>Excluded after scope review</option>
            </select>
          </label>
        </div>
        {r.information_status !== "explicit" && (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <span>
              I have confirmed this inferred need with the customer. Mark it
              explicit.
            </span>
          </label>
        )}
        <label>
          PM notes (optional)
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Context the engineering reviewer should retain"
          />
        </label>
        <div className="review-actions">
          <button
            className="primary"
            disabled={!!busy || processing || !valid || !confirmed}
            onClick={() => save("accepted")}
          >
            <Check size={15} />
            Accept scope
          </button>
          <button
            className="secondary"
            disabled={!!busy || processing || !valid}
            onClick={() => save("needs_clarification")}
          >
            Needs clarification
          </button>
          <button
            className="text-button"
            disabled={!!busy || processing || !valid}
            onClick={() => save("deferred")}
          >
            Defer
          </button>
          <button
            className="text-button danger-text"
            disabled={!!busy || processing || !valid}
            onClick={() => save("rejected")}
          >
            Exclude
          </button>
          {edit && (
            <button
              className="secondary"
              disabled={!!busy || processing || !valid}
              onClick={() => save("pending")}
            >
              Save edits
            </button>
          )}
        </div>
        {!confirmed && (
          <p className="field-help">
            Inferred or assumed scope needs customer confirmation before
            acceptance.
          </p>
        )}
      </div>
      <details className="technical-details">
        <summary>Extraction details</summary>
        <p>
          AI confidence: {r.confidence.toFixed(2)}. This score is not a
          calibrated probability of correctness.
        </p>
        <p>Origin: {r.extraction_origin || "rules"}</p>
        {!!r.supersedes?.length && <p>Refines: {r.supersedes.join(", ")}</p>}
      </details>
    </Panel>
  );
}
function TechnicalDetail({ requirement: r }: { requirement: Requirement }) {
  const { c, busy, processing, review, setStage } = useWorkspace();
  const [reason, setReason] = useState(""),
    [notes, setNotes] = useState("");
  const a = c?.assessments.find((a) => a.requirement_id === r.id);
  if (!a)
    return (
      <Panel title="Assessment unavailable">
        <p>
          Reanalyse the conversation to generate a source-grounded assessment.
        </p>
      </Panel>
    );
  const blocked = r.pm_status !== "accepted";
  return (
    <Panel title={r.title} eyebrow="TECHNICAL REVIEW">
      <div className="inline">
        <Badge
          tone={
            a.status === "supported"
              ? "green"
              : a.status === "unsupported"
                ? "red"
                : "amber"
          }
        >
          {a.status === "conditional"
            ? "Conditionally supported"
            : pretty(a.status)}
        </Badge>
        <Badge tone={a.reviewer_status === "approved" ? "green" : ""}>
          {pretty(a.reviewer_status)}
        </Badge>
      </div>
      {blocked && (
        <div className="note amber">
          <strong>PM scope review comes first.</strong>
          <p>
            This requirement is {pretty(r.pm_status).toLowerCase()}. Confirm its
            scope before approving a technical commitment.
          </p>
          <button
            className="text-button"
            onClick={() => setStage("requirements")}
          >
            Open PM review <ArrowRight size={14} />
          </button>
        </div>
      )}
      <p className="assessment-explanation">{a.explanation}</p>
      <Sources ids={a.documentation_sources} />
      <div className="requirement-evidence">
        <span className="eyebrow">CUSTOMER REQUEST</span>
        <p>{r.description}</p>
        <EvidenceLink items={r.evidence} />
      </div>
      <DetailList title="Dependencies & conditions" items={a.dependencies} />
      <DetailList title="Technical risks" items={a.risks} />
      <DetailList title="Open questions" items={a.clarification_questions} />
      <DetailList
        title="Acceptance checks to review"
        items={r.acceptance_criteria}
      />
      <EngineeringEditor
        assessment={a}
        disabled={!!busy || processing || blocked}
        onSave={(changes, why) =>
          void review("engineering", r.id, changes, why)
        }
      />
      <div className="review-form">
        <label>
          Review basis
          <select value={reason} onChange={(e) => setReason(e.target.value)}>
            <option value="">Choose after checking the sources</option>
            <option>Reviewed documentation and preserved all conditions</option>
            <option>
              Insufficient documentation; uncertainty remains explicit
            </option>
            <option>Further technical clarification is required</option>
          </select>
        </label>
        <label>
          Technical notes (optional)
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
        <div className="review-actions">
          <button
            className="primary"
            disabled={!!busy || processing || blocked || !reason}
            onClick={() =>
              review(
                "engineering",
                r.id,
                { reviewer_status: "approved", notes: notes || a.notes },
                reason,
              )
            }
          >
            <Check size={15} />
            Approve assessment
          </button>
          <button
            className="secondary"
            disabled={!!busy || processing || blocked || !reason}
            onClick={() =>
              review(
                "engineering",
                r.id,
                { reviewer_status: "rejected", notes: notes || a.notes },
                reason,
              )
            }
          >
            Request revision
          </button>
        </div>
      </div>
      <p className="field-help">
        Approval records your review; it does not turn conditional or unknown
        support into a guarantee.
      </p>
    </Panel>
  );
}
