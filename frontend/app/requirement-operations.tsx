"use client";
import { useEffect, useState } from "react";
import type { Requirement } from "./types";
export function RequirementOperations({
  requirements,
  version,
  disabled,
  onSave,
}: {
  requirements: Requirement[];
  version: number;
  disabled: boolean;
  onSave: (
    action: string,
    changes: Record<string, unknown>,
    reason: string,
  ) => void;
}) {
  const [ids, setIds] = useState<string[]>([]),
    [operation, setOperation] = useState(""),
    [title, setTitle] = useState(""),
    [description, setDescription] = useState(""),
    [parts, setParts] = useState(""),
    [reason, setReason] = useState("");
  useEffect(() => {
    setIds([]);
    setOperation("");
    setReason("");
  }, [version]);
  return (
    <details className="refinement-tools">
      <summary>Group, merge or split requirements</summary>
      <p className="muted">
        Refinements preserve source records, quotes and acceptance checks. New
        scope starts as inferred / technically unknown and requires fresh
        confirmation and reviews.
      </p>
      <div className="refinement-options">
        {requirements
          .filter((r) => !r.superseded_by?.length)
          .map((r) => (
            <label className="checkbox" key={r.id}>
              <input
                disabled={disabled}
                type="checkbox"
                checked={ids.includes(r.id)}
                onChange={(e) =>
                  setIds(
                    e.target.checked
                      ? [...ids, r.id]
                      : ids.filter((x) => x !== r.id),
                  )
                }
              />
              {r.title}
            </label>
          ))}
      </div>
      <div className="inline">
        <button
          className="secondary"
          disabled={disabled || ids.length < 2}
          onClick={() => setOperation("merge")}
        >
          Merge selected ({ids.length})
        </button>
        <button
          className="secondary"
          disabled={disabled || ids.length !== 1}
          onClick={() => setOperation("split")}
        >
          Split selected requirement
        </button>
      </div>
      {operation && (
        <div className="refinement-form">
          {operation === "merge" ? (
            <>
              <label>
                Merged title
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label>
                Merged description
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </label>
            </>
          ) : (
            <label>
              Child requirements — one per line: Title | Description
              <textarea
                rows={4}
                value={parts}
                onChange={(e) => setParts(e.target.value)}
                placeholder={
                  "Partner access | Show assigned repair records only\nOwner privacy | Hide owner personal information from partner views"
                }
              />
            </label>
          )}
          <label>
            Reason for refinement
            <input value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <button
            className="primary"
            disabled={
              disabled ||
              !reason.trim() ||
              (operation === "merge"
                ? !title.trim() || !description.trim()
                : !parts.trim())
            }
            onClick={() =>
              onSave(
                operation,
                operation === "merge"
                  ? { ids, title, description }
                  : {
                      ids,
                      parts: parts
                        .split("\n")
                        .filter(Boolean)
                        .map((line) => {
                          const [title, ...rest] = line.split("|");
                          return {
                            title: title.trim(),
                            description: rest.join("|").trim(),
                          };
                        }),
                    },
                reason,
              )
            }
          >
            Create reviewable refinement
          </button>
          <button className="text-button" onClick={() => setOperation("")}>
            Cancel
          </button>
        </div>
      )}
    </details>
  );
}
