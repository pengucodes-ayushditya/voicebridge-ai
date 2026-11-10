"use client";
import { useEffect, useState } from "react";
import { ArrowRight, BarChart3, MessageSquare } from "lucide-react";
import { api } from "../api";
import { CommunicationExperiment } from "../workflow-tools";
import type { Domain, Evidence } from "../types";
import { useWorkspace } from "./context";
import { Badge, EmptyState, Panel, pretty } from "./ui";
type Data = {
  sample_size: number;
  ready_count: number;
  reviewed_responses: number;
  observation_counts: Record<string, number>;
  observations: {
    id: string;
    kind: string;
    description: string;
    information_status: string;
    evidence: Evidence[];
    conversation_id: string;
    conversation_title: string;
  }[];
  language_counts: Record<string, number>;
  data_insufficient: boolean;
  caveat: string;
};
export function InsightsView() {
  const { domain, setDomain, run, select } = useWorkspace();
  const [data, setData] = useState<Data | null>(null),
    [kind, setKind] = useState("all");
  useEffect(() => {
    let active = true;
    void run("Loading conversation insights", () =>
      api<Data>("/insights?domain_id=" + domain),
    ).then((r) => {
      if (active && r) setData(r);
    });
    return () => {
      active = false;
    };
  }, [domain, run]);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">COMMUNICATION INSIGHTS</span>
          <h1>
            Learn from the words.
            <br />
            Keep the context.
          </h1>
          <p>
            Evidence-linked questions, concerns and constraints across your
            saved conversations.
          </p>
        </div>
        <label className="compact-label">
          Product scenario
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
      {data && (
        <>
          <div className="insight-metrics">
            {[
              [data.sample_size, "saved conversations"],
              [data.ready_count, "ready for review"],
              [data.observation_counts.question || 0, "question observations"],
              [data.reviewed_responses, "approved responses"],
            ].map(([number, label]) => (
              <div className="metric-card" key={label}>
                <strong>{number}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
          {data.sample_size === 0 ? (
            <div className="note">
              <BarChart3 size={21} />
              <div>
                <strong>No conversation data yet.</strong>
                <p>
                  Open a saved conversation or create an example to see
                  evidence-linked questions, concerns and language coverage.
                  This view will show patterns after conversations are added.
                </p>
              </div>
            </div>
          ) : data.data_insufficient && (
            <div className="note">
              <BarChart3 size={21} />
              <div>
                <strong>
                  Early descriptive signals, not a performance benchmark.
                </strong>
                <p>
                  Sample: {data.sample_size} synthetic conversations. The
                  collection is too small for general claims about customer
                  satisfaction or sales outcomes.
                </p>
              </div>
            </div>
          )}
          <div className="insights-layout">
            <Panel
              title="Conversation moments"
              action={
                <select
                  aria-label="Filter communication moments"
                  value={kind}
                  onChange={(e) => setKind(e.target.value)}
                >
                  <option value="all">All moments</option>
                  <option value="question">Questions</option>
                  <option value="objection">Objections</option>
                  <option value="constraint">Constraints</option>
                  <option value="sentiment">Expressed sentiment</option>
                </select>
              }
            >
              {data.observations.filter(
                (o) => kind === "all" || o.kind === kind,
              ).length ? (
                data.observations
                  .filter((o) => kind === "all" || o.kind === kind)
                  .map((o, i) => (
                    <article
                      className="insight-moment"
                      key={o.conversation_id + o.id + i}
                    >
                      <div className="inline spread">
                        <Badge>{pretty(o.kind)}</Badge>
                        <span className="small muted">
                          {pretty(o.information_status)}
                        </span>
                      </div>
                      <h3>{o.description}</h3>
                      {o.evidence[0] && (
                        <blockquote>“{o.evidence[0].quote}”</blockquote>
                      )}
                      <button
                        className="text-button"
                        onClick={() =>
                          select(o.conversation_id, "conversation")
                        }
                      >
                        {o.conversation_title}
                        <ArrowRight size={14} />
                      </button>
                    </article>
                  ))
              ) : (
                <EmptyState title="No moments in this view">
                  Analyse a conversation to build evidence-linked insights.
                </EmptyState>
              )}
            </Panel>
            <aside>
              <Panel title="Language coverage">
                {Object.entries(data.language_counts).map(
                  ([language, count]) => (
                    <div className="language-row" key={language}>
                      <span>
                        {language === "unknown"
                          ? "Not returned / unassigned"
                          : language}
                      </span>
                      <strong>{count}</strong>
                    </div>
                  ),
                )}
                {!Object.keys(data.language_counts).length && (
                  <p className="muted">No language observations yet.</p>
                )}
              </Panel>
              <Panel title="Read the signals carefully">
                <MessageSquare size={24} />
                <p>
                  Expressed concern or interest comes from customer wording.
                  Audio energy and pauses are measured separately within each
                  recorded conversation.
                </p>
                <p className="muted">
                  They do not establish internal emotion, satisfaction scores or
                  causal impact.
                </p>
              </Panel>
            </aside>
          </div>
          <details className="advanced-panel">
            <summary>Authored pitch comparison experiment</summary>
            <div className="advanced-body">
              <p className="muted">
                A separate six-run scripted device-lifecycle example
                demonstrates the comparison mechanism. Its outcomes are authored
                fixtures, not observed customer behavior.
              </p>
              <CommunicationExperiment />
            </div>
          </details>
        </>
      )}
    </>
  );
}
