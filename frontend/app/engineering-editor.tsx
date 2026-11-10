"use client";
import { useState } from "react";
import type { Assessment } from "./types";
export function EngineeringEditor({
  assessment,
  disabled,
  onSave,
}: {
  assessment: Assessment;
  disabled: boolean;
  onSave: (changes: Record<string, unknown>, reason: string) => void;
}) {
  const [open, setOpen] = useState(false),
    [draft, setDraft] = useState(assessment),
    [reason, setReason] = useState("");
  if (!open)
    return (
      <button
        className="text-button"
        disabled={disabled}
        onClick={() => {
          setDraft(assessment);
          setOpen(true);
        }}
      >
        Edit technical assessment
      </button>
    );
  return (
    <div className="technical-editor">
      <label>
        Feasibility
        <select
          value={draft.status}
          onChange={(e) => setDraft({ ...draft, status: e.target.value })}
        >
          {["supported", "conditional", "unsupported", "unknown"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <p className="hint">
        Use the documented status or conservatively mark unknown. New claims
        require new approved catalogue evidence.
      </p>
      <label>
        Technical rationale
        <textarea
          value={draft.explanation}
          onChange={(e) => setDraft({ ...draft, explanation: e.target.value })}
        />
      </label>
      <label>
        Dependencies (one per line)
        <textarea
          value={draft.dependencies.join("\n")}
          onChange={(e) =>
            setDraft({
              ...draft,
              dependencies: e.target.value.split("\n").filter(Boolean),
            })
          }
        />
      </label>
      <label>
        Reviewer notes
        <textarea
          value={draft.notes}
          onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
        />
      </label>
      <label>
        Reason for revision
        <input value={reason} onChange={(e) => setReason(e.target.value)} />
      </label>
      <div className="inline">
        <button
          className="secondary"
          disabled={disabled || !reason.trim()}
          onClick={() => {
            onSave(
              {
                status: draft.status,
                explanation: draft.explanation,
                dependencies: draft.dependencies,
                notes: draft.notes,
                reviewer_status: "pending",
              },
              reason,
            );
            setOpen(false);
          }}
        >
          Save for re-review
        </button>
        <button className="text-button" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </div>
  );
}
