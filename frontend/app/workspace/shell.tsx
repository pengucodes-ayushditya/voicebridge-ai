"use client";
import { useState } from "react";
import {
  AudioLines,
  Activity,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  GraduationCap,
  History,
  LayoutDashboard,
  MessageSquare,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "../api";
import type { Domain, Providers, Stage } from "../types";
import { useWorkspace } from "./context";
import { Badge, EmptyState, EvidenceDrawer, Modal, Panel, pretty } from "./ui";
import { Intake } from "./intake";
import { ConversationStage } from "./conversation";
import { SalesStage } from "./sales";
import { RequirementsStage } from "./requirements";
import { ResponseStage } from "./response";
import { Academy } from "./academy";
import { InsightsView } from "./insights";
import { KnowledgeDrafts } from "../workflow-tools";
const steps: { id: Stage; label: string; detail: string }[] = [
  { id: "conversation", label: "Conversation", detail: "Listen & understand" },
  { id: "sales", label: "Sales Copilot", detail: "Answer with evidence" },
  { id: "requirements", label: "Requirements", detail: "Confirm the scope" },
  { id: "engineering", label: "Engineering", detail: "Review feasibility" },
  { id: "response", label: "Customer response", detail: "Close the loop" },
];
export function Shell() {
  const w = useWorkspace();
  const [deleting, setDeleting] = useState(false);
  const { view, setView, c, stage, setStage, journey, busy, processing } = w;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" onClick={() => setView("overview")}>
          <AudioLines size={28} />
          <span>
            VoiceBridge <b>AI</b>
          </span>
        </button>
        <div className="sidebar-caption">CUSTOMER INTENT, CARRIED THROUGH.</div>
        <nav>
          {(
            [
              ["overview", "Workspace", LayoutDashboard],
              ["academy", "Sales Academy", GraduationCap],
              ["insights", "Insights", Activity],
              ["knowledge", "Product knowledge", BookOpen],
            ] as const
          ).map(([id, label, Icon]) => (
            <button
              key={id}
              className={
                view === id || (id === "overview" && view === "workspace")
                  ? "active"
                  : ""
              }
              onClick={() => setView(id)}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={21} />
          <strong>Every handoff has a source.</strong>
          <p>
            Customer evidence, product knowledge and human review in one
            connected workflow.
          </p>
        </div>
        <div className="provider-mini">
          <span className={w.online ? "status-dot" : "status-dot offline"} />
          {w.online ? "Local workspace connected" : "API offline"}
          <small>
            {w.providers?.reasoning.model || "Reasoning not configured"}
          </small>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span>
            {view === "workspace" && c && (
              <>
                <ChevronRight size={13} />
                <strong>{c.title}</strong>
              </>
            )}
            {view !== "overview" && view !== "workspace" && (
              <>
                <ChevronRight size={13} />
                <strong>{pretty(view)}</strong>
              </>
            )}
          </div>
          <button
            className="primary"
            disabled={!!busy}
            onClick={() => w.setIntake(true)}
          >
            <Plus size={16} />
            New conversation
          </button>
        </header>
        <main>
          {w.error && (
            <div className="error-banner" role="alert">
              <div>
                <strong>Action needs attention</strong>
                <p>{w.error}</p>
              </div>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => w.setError("")}
              >
                <X size={17} />
              </button>
              {!w.online && (
                <button
                  className="secondary"
                  onClick={() => w.run("Reconnecting", w.refresh)}
                >
                  Reconnect
                </button>
              )}
            </div>
          )}
          {w.loading ? (
            <EmptyState title="Opening your workspace">
              Loading saved conversations and approved product sources.
            </EmptyState>
          ) : view === "overview" ? (
            <Overview />
          ) : view === "academy" ? (
            <Academy />
          ) : view === "insights" ? (
            <InsightsView />
          ) : view === "knowledge" ? (
            <KnowledgeView />
          ) : c ? (
            <>
              <div className="workspace-meta">
                <button
                  className="text-button danger-text"
                  onClick={() => setDeleting(true)}
                >
                  Delete conversation
                </button>
                <button
                  className="icon-button"
                  aria-label="Reload conversation"
                  disabled={!!busy}
                  onClick={() => w.select(c.id, stage)}
                >
                  <RefreshCw size={16} />
                </button>
                <div>
                  <Badge>
                    {c.domain_id === "marketplace"
                      ? "Marketplace intelligence"
                      : "Device lifecycle & repair"}
                  </Badge>
                  <span className="muted small">
                    Version {c.version} · {pretty(c.status)}
                  </span>
                </div>
                <button
                  className="text-button"
                  onClick={() => w.setDrawer({ kind: "history" })}
                >
                  <History size={15} />
                  Review history
                </button>
              </div>
              <nav
                className="workflow-steps"
                aria-label="Conversation workflow"
              >
                {steps.map((s, i) => {
                  const state = journey?.steps.find(
                    (n) => n.id === s.id,
                  )?.state;
                  return (
                    <button
                      key={s.id}
                      className={(stage === s.id ? "current " : "") + state}
                      aria-current={stage === s.id ? "step" : undefined}
                      onClick={() => setStage(s.id)}
                    >
                      <span className="step-number">
                        {state === "complete" ? <Check size={17} /> : i + 1}
                      </span>
                      <span>
                        <strong>{s.label}</strong>
                        <small>{s.detail}</small>
                      </span>
                    </button>
                  );
                })}
              </nav>
              {processing && (
                <div className="processing-banner" role="status">
                  <RefreshCw className="spin" size={20} />
                  <div>
                    <strong>{pretty(c.processing_step || c.status)}</strong>
                    <p>
                      Your conversation is saved. Results update here as each AI
                      step completes.
                    </p>
                  </div>
                </div>
              )}
              {c.status === "failed" && (
                <div className="error-banner">
                  <div>
                    <strong>Processing could not finish</strong>
                    <p>{c.error}</p>
                  </div>
                  <button
                    className="secondary"
                    disabled={!!busy}
                    onClick={() =>
                      c.audio_path && !c.segments.length
                        ? w.run("Resuming saved speech job", async () => {
                            const next = await api<
                              import("../types").Conversation
                            >(`/conversations/${c.id}/transcribe`, {});
                            w.apply(next);
                          })
                        : w.review("analyse")
                    }
                  >
                    {c.audio_path && !c.segments.length
                      ? "Resume transcription"
                      : "Retry analysis"}
                  </button>
                </div>
              )}
              {stage === "conversation" ? (
                <ConversationStage />
              ) : stage === "sales" ? (
                <SalesStage />
              ) : stage === "requirements" ? (
                <RequirementsStage />
              ) : stage === "engineering" ? (
                <RequirementsStage engineering />
              ) : (
                <ResponseStage />
              )}
            </>
          ) : (
            <EmptyState title="Choose a conversation">
              Open a saved conversation or start a new one.
            </EmptyState>
          )}
        </main>
        <footer className="app-footer">
          VoiceBridge AI{" "}
          <span>Evidence-led assistance. Human-reviewed commitments.</span>
        </footer>
      </div>
      {busy && (
        <div className="busy-toast" role="status">
          <RefreshCw className="spin" size={16} />
          {busy}…
        </div>
      )}
      {w.notice && (
        <div className="notice-toast" role="status">
          <Check size={17} />
          {w.notice}
        </div>
      )}
      {deleting && (
        <Modal
          title="Delete this conversation?"
          onClose={() => setDeleting(false)}
        >
          <p>
            This removes the saved conversation, its local recording, generated
            audio and review history. Export a handoff first if you need to keep
            it.
          </p>
          <div className="modal-footer">
            <button className="secondary" onClick={() => setDeleting(false)}>
              Keep conversation
            </button>
            <button
              className="danger"
              disabled={!!busy}
              onClick={async () => {
                if (await w.remove()) setDeleting(false);
              }}
            >
              Delete permanently
            </button>
          </div>
        </Modal>
      )}
      {w.intake && <Intake />}
      <EvidenceDrawer />
    </div>
  );
}
function Overview() {
  const w = useWorkspace();
  const [search, setSearch] = useState("");
  return (
    <>
      <div className="overview-hero">
        <div>
          <span className="eyebrow">
            ONE CONVERSATION. ONE CONNECTED WORKFLOW.
          </span>
          <h1>
            A better answer.
            <br />A clearer handoff.
          </h1>
          <p>
            Help sales answer the customer, turn their words into requirements
            and bring a reviewed response back.
          </p>
          <button className="primary" onClick={() => w.setIntake(true)}>
            Start a conversation <ArrowRight size={16} />
          </button>
        </div>
        <div className="hero-workflow">
          <div className="hero-people">
            <div className="portrait customer-portrait" />
            <div className="wave-decoration">▂ ▃ ▅ ▆ ▃ ▂ ▅ ▇ ▅ ▃ ▂</div>
            <div className="portrait sales-portrait" />
          </div>
          <div className="hero-quote">
            “How do we recommend a product with no history?”
          </div>
          <div className="hero-answer">
            <Sparkles size={18} />
            <span>Answer grounded in approved product knowledge.</span>
            <Check size={17} />
          </div>
          <div className="hero-track">
            <span>Customer</span>
            <ChevronRight size={14} />
            <span>Sales</span>
            <ChevronRight size={14} />
            <span>Engineering</span>
            <ChevronRight size={14} />
            <span>Customer</span>
          </div>
        </div>
      </div>
      <div className="example-row">
        <div>
          <span className="eyebrow">EXPLORE A COMPLETE EXAMPLE</span>
          <h2>Start with a familiar customer problem.</h2>
          <p className="muted">
            Synthetic transcripts run through the same analysis and review
            workflow.
          </p>
        </div>
        <button
          className="example-card"
          disabled={!!w.busy}
          onClick={() => w.loadDemo("marketplace")}
        >
          <MessageSquare size={22} />
          <span>
            <strong>Marketplace cold-start</strong>
            <small>New products. No interaction history.</small>
          </span>
          <ArrowRight size={18} />
        </button>
        <button
          className="example-card"
          disabled={!!w.busy}
          onClick={() => w.loadDemo("synthetic-device-lifecycle")}
        >
          <ShieldCheck size={22} />
          <span>
            <strong>Device lifecycle & repair</strong>
            <small>Privacy, access and realistic commitments.</small>
          </span>
          <ArrowRight size={18} />
        </button>
      </div>
      <Panel
        title="Your conversations"
        action={
          <label className="search-field">
            <Search size={15} />
            <input
              aria-label="Search conversations"
              placeholder="Find a conversation…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
        }
      >
        {w.list.length ? (
          <div className="conversation-table">
            {w.list
              .filter((c) =>
                c.title.toLowerCase().includes(search.toLowerCase()),
              )
              .map((c) => (
                <button
                  key={c.id}
                  className="conversation-row"
                  onClick={() => w.select(c.id)}
                >
                  <span className="row-icon">
                    <MessageSquare size={19} />
                  </span>
                  <span>
                    <strong>{c.title}</strong>
                    <small>
                      {c.domain_id === "marketplace"
                        ? "Marketplace intelligence"
                        : "Device lifecycle & repair"}{" "}
                      · {pretty(c.source)}
                    </small>
                  </span>
                  <Badge
                    tone={
                      c.status === "ready"
                        ? "green"
                        : c.status === "failed"
                          ? "red"
                          : "amber"
                    }
                  >
                    {pretty(c.status)}
                  </Badge>
                  <span className="row-count">
                    {c.requirements} needs · {c.open_findings} open findings
                  </span>
                  <ArrowRight size={17} />
                </button>
              ))}
          </div>
        ) : (
          <EmptyState title="Your next conversation starts here">
            Upload audio, paste a transcript or open an example above.
          </EmptyState>
        )}
      </Panel>
    </>
  );
}
function KnowledgeView() {
  const w = useWorkspace();
  const [search, setSearch] = useState("");
  const docs = w.kb.filter(
    (d) =>
      (d.domain_id || "synthetic-device-lifecycle") === w.domain &&
      `${d.title} ${d.excerpt}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">THE SHARED SOURCE OF TRUTH</span>
          <h1>
            Product knowledge.
            <br />
            Ready for the conversation.
          </h1>
          <p>
            Approved documentation grounds sales assistance, practice and
            technical review.
          </p>
        </div>
        <label className="compact-label">
          Product scenario
          <select
            value={w.domain}
            onChange={(e) => w.setDomain(e.target.value as Domain)}
          >
            <option value="marketplace">Marketplace intelligence</option>
            <option value="synthetic-device-lifecycle">
              Device lifecycle & repair
            </option>
          </select>
        </label>
      </div>
      <div className="knowledge-layout">
        <div>
          <label className="search-field">
            <Search size={16} />
            <input
              placeholder="Search approved knowledge…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <div className="knowledge-grid">
            {docs.map((d) => (
              <button
                className="knowledge-card"
                key={d.id}
                onClick={() => w.showSources(d.id)}
              >
                <Badge tone="green">{d.status}</Badge>
                <h2>{d.title}</h2>
                <p>{d.excerpt}</p>
                <span className="text-button">
                  Read source <ArrowRight size={14} />
                </span>
              </button>
            ))}
          </div>
          <details className="advanced-panel">
            <summary>Add & review product documentation</summary>
            <div className="advanced-body">
              <p className="muted">
                Documentation approval is a Technical Reviewer action in this
                local demo. Drafts are excluded from AI retrieval until
                approved.
              </p>
              <KnowledgeDrafts
                key={w.domain}
                domainId={w.domain}
                role="Technical Reviewer"
                onApproved={() => void w.refresh().catch(() => {})}
              />
            </div>
          </details>
        </div>
        <ProviderPanel />
      </div>
    </>
  );
}
function ProviderPanel() {
  const w = useWorkspace();
  return (
    <Panel
      title="AI connections"
      eyebrow="ACTUAL CONFIGURED PROVIDERS"
      action={
        <button
          className="icon-button"
          aria-label="Check AI connections"
          disabled={!!w.busy}
          onClick={() =>
            w.run("Checking configured providers", async () => {
              const p = await api<Providers>("/providers/check", {});
              w.setProviders(p);
              w.notify(
                "Connection check finished. Speech checks do not consume credits.",
              );
            })
          }
        >
          <RefreshCw size={16} />
        </button>
      }
    >
      {w.providers && (
        <>
          {[
            ["Speech to text", w.providers.stt.model, w.providers.stt.status],
            [
              "Reasoning",
              w.providers.reasoning.model || w.providers.reasoning.provider,
              w.providers.reasoning.status,
            ],
            ["Customer speech", w.providers.tts.model, w.providers.tts.status],
          ].map(([label, model, status]) => (
            <div className="provider-row" key={label}>
              <span>{label}</span>
              <strong>{model}</strong>
              <small>{status}</small>
            </div>
          ))}
          <p className="field-help">
            Provider names reflect this workspace’s configuration. Generated
            answers include their actual model. Speech requests require valid
            Gnani access and credits.
          </p>
        </>
      )}
    </Panel>
  );
}
