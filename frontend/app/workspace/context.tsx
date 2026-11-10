"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { api } from "../api";
import type {
  Conversation,
  CopilotSuggestion,
  Domain,
  Evidence,
  Journey,
  Knowledge,
  Listed,
  Providers,
  Stage,
} from "../types";
export type View =
  "overview" | "workspace" | "academy" | "insights" | "knowledge";
export type Drawer =
  | { kind: "evidence"; items: Evidence[] }
  | { kind: "source"; id: string }
  | { kind: "history" };
const roleFor = (a: string) =>
  ["pm", "merge", "split"].includes(a)
    ? "Product Manager"
    : ["engineering", "finding"].includes(a)
      ? "Technical Reviewer"
      : "Sales Representative";
function useStateModel() {
  const [view, setView] = useState<View>("overview"),
    [stage, setStage] = useState<Stage>("conversation"),
    [c, setC] = useState<Conversation | null>(null),
    [list, setList] = useState<Listed[]>([]),
    [kb, setKb] = useState<Knowledge[]>([]),
    [providers, setProviders] = useState<Providers | null>(null),
    [journey, setJourney] = useState<Journey | null>(null),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [online, setOnline] = useState(false),
    [loading, setLoading] = useState(true),
    [drawer, setDrawer] = useState<Drawer | null>(null),
    [intake, setIntake] = useState(false),
    [domain, setDomain] = useState<Domain>("marketplace"),
    [highlight, setHighlight] = useState("");
  const selected = useRef<string | null>(null),
    toast = useRef<ReturnType<typeof setTimeout> | null>(null);
  const notify = useCallback((message: string) => {
    setNotice(message);
    if (toast.current) clearTimeout(toast.current);
    toast.current = setTimeout(() => setNotice(""), 5000);
  }, []);
  const refresh = useCallback(async () => {
    const r = await Promise.allSettled([
      api<Listed[]>("/conversations"),
      api<Knowledge[]>("/knowledge/documents"),
      api<Providers>("/providers/status"),
    ]);
    if (r[0].status === "fulfilled") {
      setList(r[0].value);
      setOnline(true);
    } else {
      setOnline(false);
      throw r[0].reason;
    }
    if (r[1].status === "fulfilled") setKb(r[1].value);
    if (r[2].status === "fulfilled") setProviders(r[2].value);
  }, []);
  const run = useCallback(
    async <T,>(label: string, fn: () => Promise<T>): Promise<T | undefined> => {
      setBusy(label);
      setError("");
      try {
        return await fn();
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : "That action could not be completed.",
        );
        return undefined;
      } finally {
        setBusy("");
      }
    },
    [],
  );
  const apply = useCallback(
    (updated: Conversation) => {
      if (selected.current === updated.id) setC(updated);
      void refresh().catch(() => {});
    },
    [refresh],
  );
  const open = useCallback(
    (next: Conversation, initial: Stage = "conversation") => {
      selected.current = next.id;
      setC(next);
      setDomain(next.domain_id || "synthetic-device-lifecycle");
      setView("workspace");
      setStage(initial);
      setDrawer(null);
      setHighlight("");
      localStorage.setItem("voicebridge-conversation", next.id);
    },
    [],
  );
  const select = useCallback(
    async (id: string, initial: Stage = "conversation") => {
      await run("Opening conversation", async () =>
        open(await api<Conversation>("/conversations/" + id), initial),
      );
    },
    [run, open],
  );
  useEffect(() => {
    let active = true;
    void refresh()
      .then(async () => {
        const saved = localStorage.getItem("voicebridge-conversation");
        if (saved) {
          try {
            const next = await api<Conversation>("/conversations/" + saved);
            if (active) {
              selected.current = next.id;
              setC(next);
              setDomain(next.domain_id);
            }
          } catch {
            localStorage.removeItem("voicebridge-conversation");
          }
        }
      })
      .catch(() => {
        if (active)
          setError(
            "The VoiceBridge API is offline. Start the local app, then reconnect.",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      if (toast.current) clearTimeout(toast.current);
    };
  }, [refresh]);
  useEffect(() => {
    if (!c) {
      setJourney(null);
      return;
    }
    let active = true;
    void api<Journey>(`/conversations/${c.id}/workflow`)
      .then((j) => {
        if (active) setJourney(j);
      })
      .catch((e) => {
        if (active) setError(String(e));
      });
    return () => {
      active = false;
    };
  }, [c?.id, c?.version, c?.status, c?.processing_step]);
  useEffect(() => {
    if (!c || ["ready", "failed"].includes(c.status)) return;
    let active = true,
      pending = false;
    const id = c.id;
    const timer = setInterval(async () => {
      if (pending) return;
      pending = true;
      try {
        const next = await api<Conversation>("/conversations/" + id);
        if (active && selected.current === id) {
          setC(next);
          if (["ready", "failed"].includes(next.status))
            void refresh().catch(() => {});
        }
      } catch (e) {
        if (active)
          setError(
            e instanceof Error
              ? e.message
              : "Could not refresh processing status.",
          );
      } finally {
        pending = false;
      }
    }, 1600);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [c?.id, c?.status, refresh]);
  const review = useCallback(
    async (
      action: string,
      itemId?: string,
      changes: Record<string, unknown> = {},
      reason = "",
    ) => {
      if (!c) return;
      return run(
        action === "semantic_audit"
          ? "Checking intent against the saved response"
          : action === "draft"
            ? "Writing a customer explanation"
            : "Saving review",
        async () => {
          const next = await api<Conversation>(
            `/conversations/${c.id}/review${action === "analyse" ? "?background=true" : ""}`,
            { version: c.version, action, item_id: itemId, changes, reason },
            roleFor(action),
          );
          apply(next);
          notify(
            action === "analyse"
              ? "Analysis started. Follow its progress below."
              : "Saved with source evidence and review history.",
          );
          return next;
        },
      );
    },
    [c, run, apply, notify],
  );
  const loadDemo = useCallback(
    async (example: Domain) =>
      run("Creating your example workspace", async () => {
        const next = await api<Conversation>(
          `/conversations/demo?scenario=${example}&background=true`,
          {},
        );
        open(next);
        void refresh().catch(() => {});
        return next;
      }),
    [run, open, refresh],
  );
  const ask = useCallback(
    async (question: string, language: string) => {
      if (!c) return;
      return run("Finding a grounded answer", async () => {
        const result = await api<{
          suggestion: CopilotSuggestion;
          conversation: Conversation;
        }>(`/conversations/${c.id}/copilot`, {
          question,
          language,
          version: c.version,
        });
        apply(result.conversation);
        return result.suggestion;
      });
    },
    [c, run, apply],
  );
  const remove = useCallback(async () => {
    if (!c) return;
    return run("Deleting conversation and its local artifacts", async () => {
      await api(`/conversations/${c.id}`, undefined, undefined, "DELETE");
      selected.current = null;
      setC(null);
      setJourney(null);
      setView("overview");
      localStorage.removeItem("voicebridge-conversation");
      await refresh();
      notify("Conversation and its local artifacts deleted.");
      return true;
    });
  }, [c, run, refresh, notify]);
  const showEvidence = useCallback(
      (items: Evidence[]) => setDrawer({ kind: "evidence", items }),
      [],
    ),
    showSources = useCallback(
      (id: string) => setDrawer({ kind: "source", id }),
      [],
    );
  const jumpToSegment = useCallback((id: string) => {
    setView("workspace");
    setStage("conversation");
    setDrawer(null);
    setHighlight(id);
    setTimeout(
      () =>
        document
          .getElementById("turn-" + id)
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      100,
    );
  }, []);
  const processing = !!c && !["ready", "failed"].includes(c.status);
  return {
    view,
    setView,
    stage,
    setStage,
    c,
    list,
    kb,
    providers,
    setProviders,
    journey,
    busy,
    error,
    setError,
    notice,
    online,
    loading,
    drawer,
    setDrawer,
    intake,
    setIntake,
    domain,
    setDomain,
    highlight,
    processing,
    run,
    refresh,
    apply,
    open,
    select,
    review,
    loadDemo,
    ask,
    notify,
    remove,
    showEvidence,
    showSources,
    jumpToSegment,
  };
}
type State = ReturnType<typeof useStateModel>;
const Context = createContext<State | null>(null);
export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const state = useStateModel();
  return <Context.Provider value={state}>{children}</Context.Provider>;
}
export function useWorkspace() {
  const c = useContext(Context);
  if (!c) throw new Error("Workspace provider is missing");
  return c;
}
