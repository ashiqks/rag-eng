import { useEffect, useState } from "react";
import { useStreamingChat } from "./useStreamingChat";

const STORAGE_KEY = "streaming_demo.session_id";
const USER_KEY = "streaming_demo.user_id";

function loadOrMintUser(): string {
  let u = localStorage.getItem(USER_KEY);
  if (!u) {
    u = `demo-user-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(USER_KEY, u);
  }
  return u;
}

export function App() {
  const [userId] = useState(loadOrMintUser);
  const [sessionId, setSessionId] = useState<string | null>(
    () => sessionStorage.getItem(STORAGE_KEY),
  );
  const [health, setHealth] = useState<string>("connecting…");
  const [input, setInput] = useState("");
  const stream = useStreamingChat();

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((j) => setHealth(`${j.engine} (${j.location})`))
      .catch(() => setHealth("backend offline"));
  }, []);

  async function ensureSession(): Promise<string> {
    if (sessionId) return sessionId;
    const r = await fetch("/api/genai/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_pseudo_id: userId }),
    });
    if (!r.ok) throw new Error(`session create failed: HTTP ${r.status}`);
    const j = await r.json();
    sessionStorage.setItem(STORAGE_KEY, j.session_id);
    setSessionId(j.session_id);
    return j.session_id;
  }

  function newSession() {
    sessionStorage.removeItem(STORAGE_KEY);
    setSessionId(null);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || stream.isStreaming) return;
    setInput("");
    const sid = await ensureSession();
    stream.send({ sessionId: sid, userId, text });
  }

  return (
    <>
      <header>
        <h1>Vertex AI Search · streaming demo (React)</h1>
        <div className="meta">
          <span className="pill">{health}</span>
          <span className="pill">{sessionId ? `session ${sessionId}` : "no session"}</span>
          <button type="button" className="secondary" onClick={newSession}>New chat</button>
        </div>
      </header>

      <main>
        <section className="pane">
          {stream.references.length > 0 && <Sources items={stream.references} />}
          <div className="answer">
            <span className="answer-text">{stream.text}</span>
            {stream.isStreaming && <span className="cursor">▍</span>}
          </div>
          {stream.citations.length > 0 && <CitationList items={stream.citations} />}
          {stream.error && <div className="error">{stream.error}</div>}
        </section>

        <section className="pane">
          <h2>Event log</h2>
          <pre className="event-log">
            {stream.log.map((e, i) => (
              <span key={i}>{`[t+${e.t.toFixed(2)}s] ${e.event.padEnd(10)} ${e.summary}\n`}</span>
            ))}
          </pre>
        </section>
      </main>

      <form className="composer" onSubmit={onSubmit}>
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about Gap experiments…"
          disabled={stream.isStreaming}
        />
        <div className="row">
          <button type="submit" disabled={stream.isStreaming || !input.trim()}>Send</button>
          {stream.isStreaming && (
            <button type="button" className="secondary" onClick={stream.cancel}>Stop</button>
          )}
        </div>
      </form>
    </>
  );
}

function Sources({ items }: { items: any[] }) {
  return (
    <div className="references">
      <h2>Sources</h2>
      <ol>
        {items.map((r, i) => {
          const ci = r.chunkInfo || {};
          const di = ci.documentMetadata || r.documentMetadata || {};
          const title: string = di.title || di.uri || `reference ${i}`;
          const uri: string = di.uri || "";
          const navigable = uri.startsWith("http://") || uri.startsWith("https://");
          return (
            <li key={i}>
              {navigable ? (
                <a href={uri} target="_blank" rel="noopener">{title}</a>
              ) : (
                <>
                  {title}
                  {uri && <span className="uri-hint">{uri}</span>}
                </>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function CitationList({ items }: { items: any[] }) {
  return (
    <div className="citations">
      <h3>Citations</h3>
      <ol>
        {items.map((c, i) => {
          const sources = (c.sources || [])
            .map((s: any) => s.referenceIndex ?? s.referenceId ?? "?")
            .join(", ");
          const range =
            c.startIndex != null
              ? `chars [${c.startIndex}-${c.endIndex ?? "?"}]`
              : `… char ${c.endIndex ?? "?"}`;
          return <li key={i}>{`${range} → refs ${sources}`}</li>;
        })}
      </ol>
    </div>
  );
}
