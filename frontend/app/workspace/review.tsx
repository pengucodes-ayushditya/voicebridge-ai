"use client";
import { useState } from "react";
import { Check, ShieldCheck, Sparkles } from "lucide-react";
import type { Finding } from "../types";
import { useWorkspace } from "./context";
import { Badge, EvidenceLink, Panel, pretty } from "./ui";
export function IntegrityReview() {
  const { c, busy, processing, review, providers } = useWorkspace();
  const [closed, setClosed] = useState(false);
  if (!c) return null;
  const open = c.findings.filter(
    (f) => !["resolved", "dismissed"].includes(f.reviewer_status),
  );
  const findings = closed
    ? c.findings.filter((f) =>
        ["resolved", "dismissed"].includes(f.reviewer_status),
      )
    : open;
  return (
    <Panel
      title="Intent integrity"
      eyebrow="KEEP THE CUSTOMER'S MEANING"
      action={
        <button
          className="secondary"
          disabled={
            !!busy ||
            processing ||
            !c.segments.length ||
            !providers?.reasoning.configured
          }
          onClick={() => review("semantic_audit")}
        >
          <Sparkles size={15} />
          Run AI intent check
        </button>
      }
    >
      <div className="inline spread">
        <p className="muted">
          Compare customer evidence with sales wording, scope, engineering
          decisions and the saved response.
        </p>
        <Badge
          tone={
            open.some((f) => f.severity === "high")
              ? "red"
              : open.length
                ? "amber"
                : "green"
          }
        >
          {open.length} open
        </Badge>
      </div>
      <div className="segmented-control">
        <button
          className={!closed ? "active" : ""}
          onClick={() => setClosed(false)}
        >
          Needs review ({open.length})
        </button>
        <button
          className={closed ? "active" : ""}
          onClick={() => setClosed(true)}
        >
          Resolved & dismissed ({c.findings.length - open.length})
        </button>
      </div>
      {findings.length ? (
        findings.map((f) => (
          <FindingCard key={f.id + "-" + c.version} finding={f} />
        ))
      ) : (
        <div className="integrity-clear">
          <ShieldCheck size={26} />
          <div>
            <strong>
              {closed
                ? "No completed findings yet"
                : "No open findings from the current checks"}
            </strong>
            <p>
              {c.semantic_audit
                ? `Last semantic comparison: ${c.semantic_audit.provider}. Candidates still require human judgement.`
                : "The rule checks are available. Run the AI check to compare downstream meaning."}
            </p>
          </div>
        </div>
      )}
      <p className="field-help">
        Acknowledging an issue keeps it open. High-priority issues must be
        resolved or dismissed with a reason before approval.
      </p>
    </Panel>
  );
}
function FindingCard({ finding: f }: { finding: Finding }) {
  const { busy, processing, review } = useWorkspace();
  const [status, setStatus] = useState("resolved"),
    [reason, setReason] = useState("");
  const done = ["resolved", "dismissed"].includes(f.reviewer_status);
  return (
    <article className="finding-card">
      <div className="inline spread">
        <div className="inline">
          <Badge tone={f.severity === "high" ? "red" : "amber"}>
            {f.severity} priority
          </Badge>
          <strong>{pretty(f.finding_type)}</strong>
        </div>
        <Badge>
          {f.origin === "model" ? "AI review candidate" : "Rule check"}
        </Badge>
      </div>
      <p>{f.description}</p>
      <EvidenceLink items={f.original_evidence} />
      <details>
        <summary>Compare wording & suggested correction</summary>
        <div className="comparison-grid">
          <div>
            <span className="eyebrow">DOWNSTREAM WORDING</span>
            <blockquote>{f.downstream_text}</blockquote>
          </div>
          <div>
            <span className="eyebrow">SUGGESTED CORRECTION</span>
            <p>{f.suggested_correction}</p>
          </div>
        </div>
      </details>
      {done ? (
        <div className="resolved-note">
          <Check size={15} />
          <span>
            {pretty(f.reviewer_status)} · {f.reviewer_notes}
          </span>
        </div>
      ) : (
        <div className="finding-decision">
          <label>
            Reviewer decision
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="resolved">
                Resolved after correcting or verifying the wording
              </option>
              <option value="dismissed">
                Dismissed after reviewing the evidence
              </option>
              <option value="acknowledged">
                Acknowledged · further review needed
              </option>
            </select>
          </label>
          <label>
            Reason
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="What did you correct, verify or rule out?"
            />
          </label>
          <button
            className="secondary"
            disabled={!!busy || processing || !reason.trim()}
            onClick={() =>
              review("finding", f.id, { reviewer_status: status }, reason)
            }
          >
            Save decision
          </button>
        </div>
      )}
    </article>
  );
}
