"""Smoke test v2: parse Discovery Engine :streamAnswer as a streamed JSON array.

The endpoint returns Content-Type application/json with a body like:
  [
    {"answer": {...partial...}},
    {"answer": {...partial...}},
    ...
    {"answer": {...final...}}
  ]

Each element arrives on the wire as the model generates. We parse incrementally.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

ENV_PATH = Path(__file__).resolve().parents[1] / "tests" / "eval" / ".env"
for line in ENV_PATH.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip())

PROJECT = os.environ["SEARCH_PROJECT_ID"]
LOCATION = os.environ["SEARCH_LOCATION"]
ENGINE = os.environ["SEARCH_ENGINE_ID"]
SERVING = os.environ.get("SEARCH_SERVING_CONFIG", "default_search")

BASE = (
    f"https://discoveryengine.googleapis.com/v1"
    f"/projects/{PROJECT}/locations/{LOCATION}"
    f"/collections/default_collection/engines/{ENGINE}"
)


def _token() -> str:
    import subprocess

    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True, shell=True
    ).strip()


def _headers(token: str, accept_json: bool = True) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": PROJECT,
        "Content-Type": "application/json",
        "Accept": "application/json" if accept_json else "*/*",
    }


def create_session(token: str, user: str) -> str:
    r = requests.post(
        f"{BASE}/sessions",
        headers=_headers(token),
        json={"userPseudoId": user},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["name"].rsplit("/", 1)[-1]


def iter_json_array_objects(byte_stream):
    """Yield (object, raw_chunk_arrival_time) for each top-level object in a streaming JSON array.

    Tracks brace/bracket depth and string state. Emits each top-level object
    in the array as soon as its closing brace arrives.
    """
    decoder = json.JSONDecoder()
    buf = ""
    in_string = False
    escape = False
    depth = 0
    obj_start = -1

    for chunk in byte_stream:
        if not chunk:
            continue
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        # Append and scan only the new portion
        scan_from = len(buf)
        buf += chunk

        i = scan_from
        while i < len(buf):
            ch = buf[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue
            if ch == '"':
                in_string = True
                i += 1
                continue
            if ch == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and obj_start >= 0:
                    raw = buf[obj_start : i + 1]
                    try:
                        obj = decoder.decode(raw)
                        yield obj, time.time()
                    except json.JSONDecodeError:
                        pass
                    obj_start = -1
            i += 1


def stream_answer(token: str, session_id: str, query: str) -> dict:
    url = f"{BASE}/servingConfigs/{SERVING}:streamAnswer"
    body = {
        "query": {"text": query},
        "session": (
            f"projects/{PROJECT}/locations/{LOCATION}"
            f"/collections/default_collection/engines/{ENGINE}/sessions/{session_id}"
        ),
        "answerGenerationSpec": {
            "includeCitations": True,
            "ignoreAdversarialQuery": True,
        },
    }

    print(f"\n>>> POST {url.split('/v1/')[-1]}")
    t0 = time.time()
    first_byte_at: float | None = None
    first_obj_at: float | None = None
    chunk_count = 0
    last_text = ""
    final_obj: dict | None = None

    with requests.post(url, headers=_headers(token), json=body, stream=True, timeout=120) as r:
        print(f"<<< HTTP {r.status_code}  Content-Type: {r.headers.get('Content-Type')}  "
              f"Transfer-Encoding: {r.headers.get('Transfer-Encoding')}")
        if r.status_code != 200:
            print(r.text[:1500])
            r.raise_for_status()

        def chunk_iter():
            nonlocal first_byte_at
            for ch in r.iter_content(chunk_size=None, decode_unicode=False):
                if first_byte_at is None and ch:
                    first_byte_at = time.time()
                yield ch

        for obj, arrival in iter_json_array_objects(chunk_iter()):
            if first_obj_at is None:
                first_obj_at = arrival
            chunk_count += 1
            ans = obj.get("answer") or obj
            txt = ans.get("answerText", "")
            grew = txt.startswith(last_text)
            delta_len = len(txt) - len(last_text) if grew else len(txt)
            cites = len(ans.get("citations") or [])
            refs = len(ans.get("references") or [])
            state = ans.get("state")
            print(
                f"  obj #{chunk_count:>2}  +{delta_len:>4}ch  total={len(txt):>4}  "
                f"cites={cites}  refs={refs}  state={state}  @t+{arrival - t0:.2f}s"
            )
            if txt:
                last_text = txt
            final_obj = obj

    t1 = time.time()
    print(
        f"\n<<< stream complete: {chunk_count} objects  "
        f"first-byte={(first_byte_at - t0):.2f}s  "
        f"first-obj={(first_obj_at - t0):.2f}s  "
        f"total={t1 - t0:.2f}s  "
        f"final_len={len(last_text)}"
    )
    if final_obj:
        ans = final_obj.get("answer") or final_obj
        print(
            f"<<< final: state={ans.get('state')!r}  "
            f"citations={len(ans.get('citations') or [])}  "
            f"references={len(ans.get('references') or [])}  "
            f"answer_name={ans.get('name', '')!r}"
        )
    return {"text": last_text, "chunks": chunk_count, "final": final_obj}


def non_stream_answer(token: str, session_id: str, query: str) -> dict:
    url = f"{BASE}/servingConfigs/{SERVING}:answer"
    body = {
        "query": {"text": query},
        "session": (
            f"projects/{PROJECT}/locations/{LOCATION}"
            f"/collections/default_collection/engines/{ENGINE}/sessions/{session_id}"
        ),
        "answerGenerationSpec": {"includeCitations": True},
    }
    t0 = time.time()
    r = requests.post(url, headers=_headers(token), json=body, timeout=120)
    t1 = time.time()
    r.raise_for_status()
    j = r.json()
    ans = j.get("answer", {})
    print(
        f"\n[non-stream] HTTP 200  total={t1 - t0:.2f}s  "
        f"text_len={len(ans.get('answerText', ''))}  "
        f"citations={len(ans.get('citations') or [])}  "
        f"references={len(ans.get('references') or [])}  "
        f"state={ans.get('state')}"
    )
    return j


def main() -> int:
    print(f"PROJECT={PROJECT}  LOCATION={LOCATION}  ENGINE={ENGINE}  SERVING={SERVING}")
    token = _token()
    print(f"token: {len(token)} chars")

    user = "smoke-test-streaming-v2"
    sid_a = create_session(token, user)
    sid_b = create_session(token, user)
    print(f"sessions: stream={sid_a}  non-stream={sid_b}")

    q = "What experiments have been run for the Quick Add feature on Old Navy?"

    streamed = stream_answer(token, sid_a, q)
    nonstream = non_stream_answer(token, sid_b, q)

    print("\n=== Comparison ===")
    s_text = streamed["text"]
    n_text = nonstream.get("answer", {}).get("answerText", "")
    print(f"stream final length:    {len(s_text)}")
    print(f"non-stream length:      {len(n_text)}")
    print(f"stream chunks:          {streamed['chunks']}")
    print(f"text identical:         {s_text == n_text}")
    if s_text and n_text and s_text != n_text:
        # show diff hints
        for i, (a, b) in enumerate(zip(s_text, n_text)):
            if a != b:
                print(f"first diff at char {i}: stream={a!r} nonstream={b!r}")
                print(f"  stream  ...{s_text[max(0,i-30):i+30]!r}")
                print(f"  nonstrm ...{n_text[max(0,i-30):i+30]!r}")
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
