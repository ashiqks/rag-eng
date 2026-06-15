"""Print the shape of one references frame and one citation frame from the
local backend so we can match the frontend renderer against the real fields."""
from __future__ import annotations
import json
import httpx

BASE = "http://127.0.0.1:8765"
USER = "shape-check"

s = httpx.post(f"{BASE}/api/genai/sessions", json={"user_pseudo_id": USER}, timeout=30)
s.raise_for_status()
sid = s.json()["session_id"]

with httpx.stream(
    "POST",
    f"{BASE}/api/genai/chat/stream",
    json={"text": "Quick Add Old Navy summary", "session_id": sid, "user_pseudo_id": USER},
    headers={"Accept": "text/event-stream"},
    timeout=httpx.Timeout(connect=10, read=180, write=10, pool=5),
) as r:
    buf = ""
    seen_refs = False
    seen_cite = False
    for chunk in r.iter_text():
        buf += chunk
        while "\n\n" in buf:
            frame, buf = buf.split("\n\n", 1)
            event = ""
            data_lines = []
            for line in frame.split("\n"):
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            if not data_lines:
                continue
            data = json.loads("\n".join(data_lines))
            if event == "references" and not seen_refs:
                seen_refs = True
                print("=== references[0] ===")
                print(json.dumps(data["references"][0], indent=2)[:2000])
            elif event == "citation" and not seen_cite:
                seen_cite = True
                print("=== citation chunk ===")
                print(json.dumps(data, indent=2)[:1500])
            elif event == "done":
                done = data
                print("=== done summary ===")
                print(f"state={done.get('state')}  text_len={len(done.get('answerText') or '')}")
                print(f"citations={len(done.get('citations') or [])}  references={len(done.get('references') or [])}")
                if done.get("citations"):
                    print("done.citations[0]:")
                    print(json.dumps(done["citations"][0], indent=2)[:600])
                break
        if seen_refs and seen_cite and event == "done":
            break
