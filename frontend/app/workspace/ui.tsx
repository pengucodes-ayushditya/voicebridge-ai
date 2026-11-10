"use client";
import { useEffect, useRef } from "react";
import {
  ArrowRight,
  Check,
  ChevronRight,
  FileText,
  MessageSquare,
  Search,
  X,
} from "lucide-react";
import { useWorkspace } from "./context";
import type { Evidence, Stage } from "../types";
export const pretty = (s: string) =>
  s.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const time = (ms: number | null) =>
  ms === null
    ? "No timestamp"
    : `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;
export function Badge({
  children,
  tone = "",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Panel({
  title,
  eyebrow,
  action,
  children,
  className = "",
}: {
  title: string;
  eyebrow?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={"panel " + className}>
      <header className="panel-head">
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h2>{title}</h2>
        </div>
        {action}
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}
export function Sources({ ids }: { ids: string[] }) {
  const { kb, showSources } = useWorkspace();
  return (
    <div className="sources">
      {Array.from(new Set(ids)).map((id) => (
        <button className="source" key={id} onClick={() => showSources(id)}>
          <FileText size={13} />
          {kb.find((k) => k.id === id)?.title || id}
          <ChevronRight size={12} />
        </button>
      ))}
    </div>
  );
}
export function EvidenceLink({
  items,
  label,
}: {
  items: Evidence[];
  label?: string;
}) {
  const { showEvidence } = useWorkspace();
  return (
    <button
      className="text-button"
      disabled={!items.length}
      onClick={() => showEvidence(items)}
    >
      <MessageSquare size={14} />
      {label ||
        `${items.length} customer ${items.length === 1 ? "quote" : "quotes"}`}
      <ChevronRight size={13} />
    </button>
  );
}
export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-mark">
        <MessageSquare size={25} />
      </div>
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function DetailList({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return items.length > 0 ? (
    <div className="detail-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  ) : null;
}
export function NextStep({ label, stage }: { label: string; stage: Stage }) {
  const { setStage } = useWorkspace();
  return (
    <div className="next-step">
      <div>
        <span className="eyebrow">NEXT IN THE WORKFLOW</span>
        <p>{label}</p>
      </div>
      <button
        className="primary"
        onClick={() => {
          setStage(stage);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }}
      >
        Continue <ArrowRight size={16} />
      </button>
    </div>
  );
}
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prior = document.activeElement as HTMLElement | null;
    const focus = () =>
      Array.from(
        ref.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),a[href]",
        ) || [],
      );
    focus()[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab") {
        const fields = focus(),
          first = fields[0],
          last = fields[fields.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      prior?.focus();
    };
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className={"modal " + (wide ? "wide" : "")}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="modal-header">
          <div>
            <span className="eyebrow">VOICEBRIDGE WORKSPACE</span>
            <h2>{title}</h2>
          </div>
          <button
            aria-label="Close dialog"
            className="icon-button"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}
export function EvidenceDrawer() {
  const { drawer, setDrawer, kb, c, jumpToSegment } = useWorkspace();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!drawer) return;
    const prior = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setDrawer(null);
      if (e.key === "Tab") {
        const fields = Array.from(
          ref.current?.querySelectorAll<HTMLElement>(
            "button:not(:disabled),a[href]",
          ) || [],
        );
        if (e.shiftKey && document.activeElement === fields[0]) {
          e.preventDefault();
          fields[fields.length - 1]?.focus();
        } else if (
          !e.shiftKey &&
          document.activeElement === fields[fields.length - 1]
        ) {
          e.preventDefault();
          fields[0]?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      prior?.focus();
    };
  }, [drawer, setDrawer]);
  if (!drawer) return null;
  const doc =
    drawer.kind === "source" ? kb.find((d) => d.id === drawer.id) : null;
  return (
    <div
      className="drawer-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) setDrawer(null);
      }}
    >
      <aside
        className="evidence-drawer"
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={
          drawer.kind === "history" ? "Review history" : "Source evidence"
        }
      >
        <header className="drawer-header">
          <div>
            <span className="eyebrow">TRACEABLE BY DESIGN</span>
            <h2>
              {drawer.kind === "history"
                ? "Review history"
                : drawer.kind === "source"
                  ? "Product source"
                  : "Customer evidence"}
            </h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close evidence panel"
            onClick={() => setDrawer(null)}
          >
            <X size={20} />
          </button>
        </header>
        {drawer.kind === "evidence" &&
          drawer.items.map((ev, i) => {
            const segment = c?.segments.find((s) => s.id === ev.segment_id);
            return (
              <article className="evidence-card" key={i}>
                <div className="inline">
                  <Badge tone={ev.speaker_role === "customer" ? "green" : ""}>
                    {pretty(ev.speaker_role)}
                  </Badge>
                  <span className="muted small">
                    {ev.segment_id} · {time(ev.start_ms)}
                  </span>
                </div>
                <blockquote>“{ev.quote}”</blockquote>
                {segment?.original_text &&
                  segment.original_text !== segment.text && (
                    <details>
                      <summary>Original transcription</summary>
                      <p>{segment.original_text}</p>
                    </details>
                  )}
                {segment?.parent_segment_id && (
                  <p className="small muted">
                    Split from source turn {segment.parent_segment_id};
                    individual timing is not inferred.
                  </p>
                )}
                <button
                  className="text-button"
                  onClick={() => jumpToSegment(ev.segment_id)}
                >
                  View in conversation <ArrowRight size={14} />
                </button>
              </article>
            );
          })}
        {drawer.kind === "source" &&
          (doc ? (
            <article className="source-document">
              <Badge tone="green">{doc.status}</Badge>
              <h3>{doc.title}</h3>
              <p className="muted small">
                {pretty(doc.category)} · Version {doc.version}
                <br />
                {doc.owner}
              </p>
              <div className="document-excerpt">{doc.excerpt}</div>
              <p className="source-id">{doc.id}</p>
            </article>
          ) : (
            <EmptyState title="Source not available">
              Review the knowledge library before using this claim.
            </EmptyState>
          ))}
        {drawer.kind === "history" &&
          (c?.audit_log.length ? (
            c.audit_log
              .slice()
              .reverse()
              .map((event, i) => (
                <article className="history-event" key={i}>
                  <Check size={17} />
                  <div>
                    <strong>{pretty(event.action)}</strong>
                    <p>{event.reason}</p>
                    <small>
                      {event.role} · Version {event.version}
                      <br />
                      {new Date(event.at).toLocaleString()}
                    </small>
                  </div>
                </article>
              ))
          ) : (
            <p className="muted">Review decisions will appear here.</p>
          ))}
        <div className="drawer-note">
          <Search size={16} />
          Customer wording stays separate from product documentation and
          reviewer decisions.
        </div>
      </aside>
    </div>
  );
}
