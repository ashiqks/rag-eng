/**
 * Streaming chat hook.
 *
 * Mirrors the guide's `useStreamingChat` with the same fixes the backend
 * applies on its side:
 *   - mid-stream citations always arrive as a list (`data.citations`),
 *   - `done.answerText` is accepted as the canonical final text.
 *
 * SSE consumed via fetch + ReadableStream because EventSource can't carry a
 * POST body.
 */
import { useCallback, useRef, useState } from "react";

export type LogEntry = { t: number; event: string; summary: string };

export type StreamState = {
  text: string;
  references: any[];
  citations: any[];
  isStreaming: boolean;
  error: string | null;
  answerId: string | null;
  log: LogEntry[];
};

const initial: StreamState = {
  text: "",
  references: [],
  citations: [],
  isStreaming: false,
  error: null,
  answerId: null,
  log: [],
};

type SendArgs = { sessionId: string; userId: string; text: string };

export function useStreamingChat() {
  const [state, setState] = useState<StreamState>(initial);
  const abortRef = useRef<AbortController | null>(null);
  const startedAtRef = useRef<number>(0);
  // Mid-stream citation accumulator. We use a ref instead of state so we
  // don't have to schedule a re-render purely to update the buffer that
  // `done` will overwrite anyway.
  const midCitesRef = useRef<any[]>([]);

  const send = useCallback(async ({ sessionId, userId, text }: SendArgs) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    midCitesRef.current = [];
    startedAtRef.current = performance.now();
    setState({ ...initial, isStreaming: true });

    let resp: Response;
    try {
      resp = await fetch("/api/genai/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          text,
          session_id: sessionId,
          user_pseudo_id: userId,
        }),
        signal: abortRef.current.signal,
      });
    } catch (e: any) {
      if (e.name === "AbortError") return;
      setState((s) => ({ ...s, isStreaming: false, error: e.message ?? "network error" }));
      return;
    }

    if (!resp.ok || !resp.body) {
      const detail = await resp.text().catch(() => "");
      setState((s) => ({
        ...s,
        isStreaming: false,
        error: `HTTP ${resp.status}: ${detail.slice(0, 300)}`,
      }));
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          if (frame.trim()) handleFrame(frame, setState, midCitesRef, startedAtRef.current);
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setState((s) => ({ ...s, isStreaming: false, error: e.message }));
      }
    } finally {
      setState((s) => (s.isStreaming ? { ...s, isStreaming: false } : s));
    }
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);

  return { ...state, send, cancel };
}

function handleFrame(
  frame: string,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
  midCitesRef: React.MutableRefObject<any[]>,
  startedAt: number,
) {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (!dataLines.length) return;
  let data: any;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    return;
  }

  const t = (performance.now() - startedAt) / 1000;
  const summary =
    event === "delta"
      ? `+${(data.text || "").length}ch`
      : event === "references"
        ? `n=${(data.references || []).length}`
        : event === "citation"
          ? `n=${(data.citations || []).length}`
          : event === "done"
            ? `state=${data.state} text_len=${(data.answerText || "").length}`
            : event === "error"
              ? `${data.code}: ${data.message}`
              : "";
  const logEntry: LogEntry = { t, event, summary };

  switch (event) {
    case "references":
      setState((s) => ({ ...s, references: data.references ?? [], log: [...s.log, logEntry] }));
      break;
    case "delta":
      setState((s) => ({ ...s, text: s.text + (data.text ?? ""), log: [...s.log, logEntry] }));
      break;
    case "citation":
      midCitesRef.current = [...midCitesRef.current, ...(data.citations ?? [])];
      setState((s) => ({ ...s, citations: midCitesRef.current, log: [...s.log, logEntry] }));
      break;
    case "done":
      midCitesRef.current = [];
      setState((s) => ({
        ...s,
        isStreaming: false,
        answerId: data.answer_id ?? null,
        citations: data.citations ?? s.citations,
        references: data.references ?? s.references,
        log: [...s.log, logEntry],
      }));
      break;
    case "error":
      setState((s) => ({
        ...s,
        isStreaming: false,
        error: data.message ?? "stream error",
        log: [...s.log, logEntry],
      }));
      break;
  }
}
