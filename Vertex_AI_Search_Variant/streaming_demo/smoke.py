"""Local smoke test for the streaming demo backend.

Hits POST /api/genai/sessions to mint a session, then POST /api/genai/chat/stream
and parses the SSE response. Asserts the ordering invariants documented in
Streaming_Answer_Guide.md §3 and prints per-event timing.

Run while the backend is up (default http://127.0.0.1:8765):

    python smoke.py
    python smoke.py --base http://127.0.0.1:8765 --query "..."
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Iterator

import httpx

DEFAULT_QUERY = "What experiments have been run for the Quick Add feature on Old Navy?"


def parse_sse(body_iter) -> Iterator[tuple[float, str, dict]]:
    """Yield (relative_time, event_name, data_obj) for each SSE frame."""
    t0 = time.time()
    buf = ""
    for raw in body_iter:
        if not raw:
            continue
        buf += raw
        while True:
            i = buf.find("\n\n")
            if i == -1:
                break
            frame, buf = buf[:i], buf[i + 2 :]
            if not frame.strip():
                continue
            event = "message"
            data_lines: list[str] = []
            for line in frame.split("\n"):
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            if not data_lines:
                continue
            try:
                data = json.loads("\n".join(data_lines))
            except json.JSONDecodeError as e:
                print(f"  ! non-JSON SSE frame skipped ({e}): {data_lines!r}")
                continue
            yield time.time() - t0, event, data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8765")
    p.add_argument("--query", default=DEFAULT_QUERY)
    p.add_argument("--user", default="streaming-demo-smoke")
    args = p.parse_args()

    print(f"== base: {args.base}")
    print(f"== query: {args.query}")

    # Health
    h = httpx.get(f"{args.base}/api/health", timeout=10).raise_for_status().json()
    print(f"== health: project={h['project']} engine={h['engine']}")

    # Session
    r = httpx.post(
        f"{args.base}/api/genai/sessions",
        json={"user_pseudo_id": args.user},
        timeout=30,
    )
    r.raise_for_status()
    sid = r.json()["session_id"]
    print(f"== session: {sid}")

    # Stream
    print(f"== streaming...")
    events: list[tuple[float, str, dict]] = []
    accumulated = ""
    mid_stream_citations: list[dict] = []
    with httpx.stream(
        "POST",
        f"{args.base}/api/genai/chat/stream",
        json={"text": args.query, "session_id": sid, "user_pseudo_id": args.user},
        headers={"Accept": "text/event-stream"},
        timeout=httpx.Timeout(connect=10, read=180, write=10, pool=5),
    ) as resp:
        if resp.status_code != 200:
            body = resp.read().decode("utf-8", "replace")
            print(f"!! HTTP {resp.status_code}: {body[:500]}")
            return 2
        for t, ev, data in parse_sse(resp.iter_text()):
            events.append((t, ev, data))
            if ev == "delta":
                accumulated += data.get("text", "")
                summary = f"+{len(data.get('text', ''))}ch  total={len(accumulated)}"
            elif ev == "references":
                summary = f"n={len(data.get('references') or [])}"
            elif ev == "citation":
                mid_stream_citations.extend(data.get("citations") or [])
                summary = f"n={len(data.get('citations') or [])}"
            elif ev == "done":
                summary = (
                    f"state={data.get('state')} "
                    f"cites={len(data.get('citations') or [])} "
                    f"refs={len(data.get('references') or [])} "
                    f"text_len={len(data.get('answerText') or '')}"
                )
            elif ev == "error":
                summary = f"{data.get('code')}: {data.get('message')}"
            else:
                summary = json.dumps(data)[:80]
            print(f"  [t+{t:5.2f}s] {ev:10s}  {summary}")
            if ev in ("done", "error"):
                break

    # Invariants
    print("\n== assertions")
    ok = True
    refs_idx = next((i for i, (_, e, _) in enumerate(events) if e == "references"), None)
    delta_idx = next((i for i, (_, e, _) in enumerate(events) if e == "delta"), None)
    done_idx = next((i for i, (_, e, _) in enumerate(events) if e == "done"), None)

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        status = "OK " if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [{status}] {name}{(' - ' + detail) if detail else ''}")

    check("references event present", refs_idx is not None)
    check("delta event present", delta_idx is not None)
    check("done event present", done_idx is not None)
    if refs_idx is not None and delta_idx is not None:
        check(
            "references arrives before first delta",
            refs_idx < delta_idx,
            f"refs@{refs_idx} delta@{delta_idx}",
        )
    delta_count = sum(1 for _, e, _ in events if e == "delta")
    check(">=10 deltas (incremental streaming)", delta_count >= 10, f"got {delta_count}")
    if done_idx is not None:
        done = events[done_idx][2]
        check("done.state == SUCCEEDED", done.get("state") == "SUCCEEDED", f"state={done.get('state')!r}")
        done_text = done.get("answerText") or ""
        check(
            "concatenated deltas == done.answerText",
            accumulated == done_text,
            f"acc_len={len(accumulated)} done_len={len(done_text)}",
        )
        # Catches the guide's `cites[0] if len==1 else cites` regression: any
        # multi-citation chunk would silently drop items there.
        done_cites = done.get("citations") or []
        if mid_stream_citations:
            check(
                "mid-stream citation count == done.citations count",
                len(mid_stream_citations) == len(done_cites),
                f"mid={len(mid_stream_citations)} done={len(done_cites)}",
            )
        if accumulated != done_text and done_text:
            for i, (a, b) in enumerate(zip(accumulated, done_text)):
                if a != b:
                    print(f"      first diff at char {i}: acc={a!r} done={b!r}")
                    print(f"        acc  …{accumulated[max(0, i - 20):i + 20]!r}")
                    print(f"        done …{done_text[max(0, i - 20):i + 20]!r}")
                    break

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
