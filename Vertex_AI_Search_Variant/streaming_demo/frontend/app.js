/*
 * Vanilla streaming chat client. Talks to the FastAPI backend on the same
 * origin. SSE consumed via fetch + ReadableStream because EventSource can't
 * carry a request body.
 */

const $ = (id) => document.getElementById(id);
const els = {
  health: $("health"),
  sessionPill: $("session-pill"),
  newSession: $("new-session"),
  answer: $("answer-text"),
  cursor: $("cursor"),
  references: $("references"),
  refsList: $("references-list"),
  citations: $("citations"),
  citesList: $("citations-list"),
  error: $("error"),
  log: $("event-log"),
  form: $("chat-form"),
  input: $("input"),
  send: $("send"),
  stop: $("stop"),
};

const STORAGE_KEY = "streaming_demo.session_id";
const USER_KEY = "streaming_demo.user_id";

let sessionId = null;
let userId = null;
let abortController = null;
let streamStartedAt = 0;
let midStreamCitations = [];

function logEvent(name, payload) {
  const t = ((performance.now() - streamStartedAt) / 1000).toFixed(2);
  const summary =
    name === "delta"
      ? `+${(payload?.text || "").length}ch`
      : name === "references"
        ? `n=${(payload?.references || []).length}`
        : name === "citation"
          ? `n=${(payload?.citations || []).length}`
          : name === "done"
            ? `state=${payload?.state} text_len=${(payload?.answerText || "").length}`
            : name === "error"
              ? `${payload?.code}: ${payload?.message}`
              : "";
  els.log.textContent += `[t+${t}s] ${name}  ${summary}\n`;
  els.log.scrollTop = els.log.scrollHeight;
}

function clearAnswer() {
  els.answer.textContent = "";
  els.references.classList.add("hidden");
  els.refsList.innerHTML = "";
  els.citations.classList.add("hidden");
  els.citesList.innerHTML = "";
  els.error.classList.add("hidden");
  els.error.textContent = "";
  els.log.textContent = "";
}

function renderReferences(refs) {
  els.refsList.innerHTML = "";
  refs.forEach((r, i) => {
    const li = document.createElement("li");
    const ci = r.chunkInfo || {};
    const di = ci.documentMetadata || r.documentMetadata || {};
    const title = di.title || di.uri || `reference ${i}`;
    const uri = di.uri || "";
    // gs:// URIs are bucket paths; only http(s) is browser-navigable.
    if (uri.startsWith("http://") || uri.startsWith("https://")) {
      const a = document.createElement("a");
      a.href = uri;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = title;
      li.appendChild(a);
    } else {
      li.textContent = title;
      if (uri) {
        const small = document.createElement("span");
        small.style.color = "#6b7280";
        small.style.marginLeft = "6px";
        small.textContent = uri;
        li.appendChild(small);
      }
    }
    els.refsList.appendChild(li);
  });
  if (refs.length) els.references.classList.remove("hidden");
}

function renderCitations(citations) {
  els.citesList.innerHTML = "";
  for (const c of citations) {
    const li = document.createElement("li");
    const sources = (c.sources || [])
      .map((s) => s.referenceIndex ?? s.referenceId ?? "?")
      .join(", ");
    const range =
      c.startIndex != null
        ? `chars [${c.startIndex}-${c.endIndex ?? "?"}]`
        : `… char ${c.endIndex ?? "?"}`;
    li.textContent = `${range} → refs ${sources}`;
    els.citesList.appendChild(li);
  }
  if (citations.length) els.citations.classList.remove("hidden");
}

async function ensureSession() {
  if (sessionId) return sessionId;
  if (!userId) {
    userId =
      localStorage.getItem(USER_KEY) ||
      `demo-user-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(USER_KEY, userId);
  }
  const r = await fetch("/api/genai/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_pseudo_id: userId }),
  });
  if (!r.ok) throw new Error(`session create failed: HTTP ${r.status}`);
  const j = await r.json();
  sessionId = j.session_id;
  sessionStorage.setItem(STORAGE_KEY, sessionId);
  els.sessionPill.textContent = `session ${sessionId}`;
  return sessionId;
}

function newSession() {
  sessionId = null;
  sessionStorage.removeItem(STORAGE_KEY);
  els.sessionPill.textContent = "no session";
  clearAnswer();
}

function handleFrame(frame) {
  let event = "message";
  let dataLines = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    // Preserve newlines if a future server ever splits one payload across
    // multiple `data:` lines (the SSE spec allows it; ours doesn't, but be safe).
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }
  if (!dataLines.length) return;
  let data;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch (e) {
    console.warn("non-JSON SSE payload, ignored:", dataLines);
    return;
  }
  logEvent(event, data);

  switch (event) {
    case "references":
      renderReferences(data.references || []);
      break;
    case "delta":
      els.answer.append(data.text || "");
      break;
    case "citation":
      // Mid-stream `citations` accumulate; `done` overwrites with canonical list.
      midStreamCitations.push(...(data.citations || []));
      renderCitations(midStreamCitations);
      break;
    case "done":
      midStreamCitations.length = 0;
      renderCitations(data.citations || []);
      if (data.references) renderReferences(data.references);
      els.cursor.classList.add("hidden");
      els.send.disabled = false;
      els.stop.disabled = true;
      break;
    case "error":
      els.error.textContent = `[${data.code}] ${data.message}`;
      els.error.classList.remove("hidden");
      els.cursor.classList.add("hidden");
      els.send.disabled = false;
      els.stop.disabled = true;
      break;
  }
}

async function sendQuestion(text) {
  await ensureSession();
  clearAnswer();
  els.cursor.classList.remove("hidden");
  els.send.disabled = true;
  els.stop.disabled = false;
  streamStartedAt = performance.now();
  midStreamCitations = [];

  abortController = new AbortController();
  let resp;
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
      signal: abortController.signal,
    });
  } catch (e) {
    if (e.name === "AbortError") return;
    els.error.textContent = `network error: ${e.message}`;
    els.error.classList.remove("hidden");
    els.cursor.classList.add("hidden");
    els.send.disabled = false;
    els.stop.disabled = true;
    return;
  }

  if (!resp.ok || !resp.body) {
    const detail = await resp.text().catch(() => "");
    els.error.textContent = `HTTP ${resp.status}: ${detail.slice(0, 300)}`;
    els.error.classList.remove("hidden");
    els.cursor.classList.add("hidden");
    els.send.disabled = false;
    els.stop.disabled = true;
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
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        if (frame.trim()) handleFrame(frame);
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") {
      els.error.textContent = `read error: ${e.message}`;
      els.error.classList.remove("hidden");
    }
  } finally {
    els.cursor.classList.add("hidden");
    els.send.disabled = false;
    els.stop.disabled = true;
  }
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = els.input.value.trim();
  if (!text) return;
  els.input.value = "";
  sendQuestion(text);
});

els.stop.addEventListener("click", () => abortController?.abort());
els.newSession.addEventListener("click", newSession);

(async function init() {
  try {
    const r = await fetch("/api/health");
    const j = await r.json();
    els.health.textContent = `${j.engine} (${j.location})`;
  } catch {
    els.health.textContent = "backend offline";
  }
  sessionId = sessionStorage.getItem(STORAGE_KEY);
  if (sessionId) els.sessionPill.textContent = `session ${sessionId}`;
})();
