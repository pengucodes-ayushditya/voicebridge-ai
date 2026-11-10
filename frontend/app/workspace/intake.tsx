"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { FileAudio, FileText, Mic, Square, Upload } from "lucide-react";
import { api, uploadAudio } from "../api";
import type { Conversation, Domain, Segment } from "../types";
import { useWorkspace } from "./context";
import { Modal } from "./ui";
const examples: Record<Domain, string> = {
  marketplace:
    "Customer: We run an online marketplace. New products have no clicks, reviews or purchase history. We need to recommend them to the right customers.\nSales: Which product information is available?\nCustomer: We have descriptions and images. Recommendation accuracy is my main concern. Let's agree on a pilot and evaluation criteria.",
  "synthetic-device-lifecycle":
    "Customer: Humein har device ki QR repair history chahiye. Repair partners ko owner ka naam aur phone nahi dikhna chahiye.\nSales: ERP integration depends on API compatibility.\nCustomer: Hamare ERP ki API details abhi confirm nahi hain. Pehle access permissions aur privacy test karna hai.",
};
function parse(text: string, language: string): Segment[] {
  const rows: Segment[] = [];
  for (const line of text.split("\n").filter((v) => v.trim())) {
    const match = line.match(
      /^\s*(Customer|Sales(?: representative)?|Unknown)\s*:\s*(.+)$/i,
    );
    if (match) {
      const role =
        match[1].toLowerCase() === "customer"
          ? "customer"
          : match[1].toLowerCase().startsWith("sales")
            ? "sales"
            : "unknown";
      rows.push({
        id: "t" + (rows.length + 1),
        speaker_id: role,
        role,
        text: match[2].trim(),
        original_text: match[2].trim(),
        start_ms: null,
        end_ms: null,
        language,
      });
    } else if (rows.length) {
      rows[rows.length - 1].text += "\n" + line;
      rows[rows.length - 1].original_text = rows[rows.length - 1].text;
    } else
      rows.push({
        id: "t1",
        speaker_id: "unassigned",
        role: "unknown",
        text: line.trim(),
        original_text: line.trim(),
        start_ms: null,
        end_ms: null,
        language,
      });
  }
  return rows;
}
export function Intake() {
  const { domain, setDomain, setIntake, run, open, refresh, busy, online } =
    useWorkspace();
  const [mode, setMode] = useState("upload"),
    [title, setTitle] = useState("Customer product discussion"),
    [text, setText] = useState(""),
    [consent, setConsent] = useState(false),
    [file, setFile] = useState<File | null>(null),
    [progress, setProgress] = useState<number | null>(null),
    [speechMode, setSpeechMode] = useState("rest"),
    [language, setLanguage] = useState("en"),
    [recording, setRecording] = useState(false),
    [seconds, setSeconds] = useState(0),
    [audioUrl, setAudioUrl] = useState(""),
    [mediaError, setMediaError] = useState(""),
    [canRecord, setCanRecord] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null),
    stream = useRef<MediaStream | null>(null),
    tick = useRef<ReturnType<typeof setInterval> | null>(null);
  const close = useCallback(() => setIntake(false), [setIntake]);
  useEffect(() => {
    setCanRecord(
      typeof MediaRecorder !== "undefined" &&
        !!navigator.mediaDevices?.getUserMedia,
    );
    return () => {
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      if (tick.current) clearInterval(tick.current);
    };
  }, []);
  useEffect(() => {
    if (!file) {
      setAudioUrl("");
      return;
    }
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const stop = () => {
    recorder.current?.stop();
    stream.current?.getTracks().forEach((t) => t.stop());
    if (tick.current) clearInterval(tick.current);
    setRecording(false);
  };
  async function start() {
    setMediaError("");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      const mime = ["audio/webm;codecs=opus", "audio/mp4"].find((t) =>
        MediaRecorder.isTypeSupported(t),
      );
      const rec = new MediaRecorder(
        stream.current,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = rec;
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      rec.onstop = () => {
        const blob = new Blob(chunks, { type: rec.mimeType });
        setFile(
          new File(
            [blob],
            rec.mimeType.includes("mp4")
              ? "conversation.mp4"
              : "conversation.webm",
            { type: rec.mimeType },
          ),
        );
      };
      rec.start();
      setSeconds(0);
      setRecording(true);
      tick.current = setInterval(() => setSeconds((n) => n + 1), 1000);
    } catch {
      setMediaError(
        "Microphone access was not granted or is unavailable. You can upload a recording instead.",
      );
      stream.current?.getTracks().forEach((t) => t.stop());
    }
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const next = await run(
      mode === "upload" || mode === "record"
        ? "Uploading the conversation"
        : "Creating your conversation workspace",
      async () => {
        if (mode === "upload" || mode === "record") {
          if (!file) throw new Error("Choose or record an audio file first.");
          const form = new FormData();
          form.append("file", file);
          form.append("synthetic_consent", "true");
          form.append("transcription_mode", speechMode);
          form.append("domain_id", domain);
          form.append("title", title);
          setProgress(0);
          try {
            return await uploadAudio<Conversation>(form, setProgress);
          } finally {
            setProgress(null);
          }
        }
        if (mode === "brief")
          return api<Conversation>("/sales/discovery?background=true", {
            title,
            context: text,
            domain_id: domain,
            synthetic_consent: true,
          });
        return api<Conversation>("/conversations?background=true", {
          title,
          domain_id: domain,
          segments: parse(text, language),
          synthetic_consent: true,
        });
      },
    );
    if (next) {
      open(next);
      void refresh();
      close();
    }
  }
  return (
    <Modal title="Start a conversation" onClose={close} wide>
      <p className="muted">
        Bring in a recording, a transcript or a customer brief. Each becomes one
        connected workspace.
      </p>
      <div
        className="intake-tabs"
        role="tablist"
        aria-label="Conversation input"
      >
        {[
          { id: "upload", label: "Upload audio", icon: Upload },
          { id: "paste", label: "Paste transcript", icon: FileText },
          { id: "brief", label: "Customer brief", icon: FileText },
          { id: "record", label: "Record", icon: Mic },
        ].map((m) => (
          <button
            type="button"
            role="tab"
            aria-selected={mode === m.id}
            key={m.id}
            className={mode === m.id ? "active" : ""}
            onClick={() => {
              if (recording) stop();
              setMode(m.id);
            }}
          >
            <m.icon size={16} />
            {m.label}
          </button>
        ))}
      </div>
      <form onSubmit={submit}>
        <div className="form-grid">
          <label>
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
          <label>
            Conversation title
            <input
              required
              value={title}
              maxLength={120}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
        </div>
        {(mode === "upload" || mode === "record") && (
          <>
            <div className="upload-zone">
              {mode === "upload" ? (
                <>
                  <FileAudio size={35} />
                  <strong>Choose a customer conversation</strong>
                  <span>
                    WAV, MP3, M4A, WebM, OGG, FLAC or MP4 · up to 10 MiB
                  </span>
                  <input
                    aria-label="Conversation audio file"
                    type="file"
                    accept=".wav,.mp3,.m4a,.webm,.ogg,.flac,.aac,.amr,.opus,.mp4"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </>
              ) : (
                <>
                  <Mic size={32} />
                  <strong>
                    {recording
                      ? `Recording ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
                      : "Record a fictional conversation"}
                  </strong>
                  <p>
                    Record first, then transcribe and review. This is not a live
                    calling service.
                  </p>
                  <button
                    type="button"
                    className={recording ? "danger-button" : "secondary"}
                    disabled={!canRecord}
                    onClick={recording ? stop : start}
                  >
                    {recording ? (
                      <>
                        <Square size={15} />
                        Stop recording
                      </>
                    ) : (
                      <>
                        <Mic size={16} />
                        Start recording
                      </>
                    )}
                  </button>
                  {!canRecord && (
                    <p className="small">
                      This browser does not support recording. Use Upload audio.
                    </p>
                  )}
                  {mediaError && <p role="alert">{mediaError}</p>}
                </>
              )}
            </div>
            {file && (
              <div className="recording-preview">
                <strong>{file.name}</strong>
                <span className="muted small">
                  {(file.size / 1024 / 1024).toFixed(2)} MiB
                </span>
                {audioUrl && <audio controls src={audioUrl} />}
              </div>
            )}
            <label>
              Speech processing
              <select
                value={speechMode}
                onChange={(e) => setSpeechMode(e.target.value)}
              >
                <option value="rest">Quick clip · up to 30 seconds</option>
                <option value="batch">
                  Longer conversation · Batch with speaker separation
                </option>
              </select>
            </label>
            <p className="field-help">
              {speechMode === "rest"
                ? "Prisma short-clip transcription returns text without speaker separation. Review and split turns before analysis."
                : "Prisma processes Batch jobs asynchronously. You can leave the workspace open while processing; vendor queues can take time."}
            </p>
          </>
        )}
        {(mode === "paste" || mode === "brief") && (
          <>
            <label>
              {mode === "brief"
                ? "Customer context and questions"
                : "Transcript"}
              <textarea
                rows={9}
                required
                minLength={10}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={
                  mode === "brief"
                    ? "Describe the customer's business, needs, constraints and unanswered questions…"
                    : examples[domain]
                }
              />
            </label>
            {mode === "paste" && (
              <div className="inline spread">
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setText(examples[domain])}
                >
                  Use example wording
                </button>
                <label className="compact-label">
                  Language
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="hi-en">Hinglish</option>
                  </select>
                </label>
              </div>
            )}
            <p className="field-help">
              {mode === "paste"
                ? "Prefix turns with Customer: or Sales:. Pasted text does not invoke a speech model."
                : "A brief can prepare Sales Copilot before you have a recording."}
            </p>
          </>
        )}
        <label className="checkbox">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span>
            This contains fictional customer information; everyone recorded has
            consented.
          </span>
        </label>
        {progress !== null && (
          <div role="status">
            <progress value={progress} max={100} />
            <span>Uploading · {progress}%</span>
          </div>
        )}
        <div className="modal-footer">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={
              !!busy ||
              !online ||
              !consent ||
              recording ||
              (mode === "upload" || mode === "record"
                ? !file
                : text.trim().length < 10)
            }
          >
            {busy ||
              (mode === "upload" || mode === "record"
                ? "Transcribe conversation"
                : "Create workspace")}
          </button>
        </div>
      </form>
    </Modal>
  );
}
