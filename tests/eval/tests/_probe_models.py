"""Probe candidate modelVersion strings against the :answer API."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import argparse
from run_eval import ask, build_answer_url, get_access_token  # noqa: E402
from configs import CONFIGS, apply_overlay  # noqa: E402
import requests  # noqa: E402

cfg = argparse.Namespace(
    search_project_id=os.environ["SEARCH_PROJECT_ID"],
    search_location=os.environ.get("SEARCH_LOCATION", "global"),
    search_collection=os.environ.get("SEARCH_COLLECTION", "default_collection"),
    search_engine_id=os.environ["SEARCH_ENGINE_ID"],
    search_serving_config=os.environ.get("SEARCH_SERVING_CONFIG", "default_search"),
)
url = build_answer_url(cfg)
tok = get_access_token()
headers = {
    "Authorization": f"Bearer {tok}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": cfg.search_project_id,
}

candidates = [
    "gemini-2.5-pro/answer_gen/v1",
    "gemini-2.5-pro/answer_gen/v2",
    "gemini-2.5-pro-preview/answer_gen/v1",
    "gemini-2.5-pro-001/answer_gen/v1",
    "stable",
    "preview",
    "gemini-2.0-flash-001/answer_gen/v1",
    "gemini-2.5-flash/answer_gen/v1",
    "gemini-2.5-flash-lite/answer_gen/v1",
    "gemini-2.5-flash/answer_gen/v2",
    "gemini-1.5-pro-002/answer_gen/v1",
]
for v in candidates:
    body = {
        "query": {"text": "ping"},
        "answerGenerationSpec": {
            "includeCitations": True,
            "ignoreAdversarialQuery": True,
            "ignoreNonAnswerSeekingQuery": False,
            "modelSpec": {"modelVersion": v},
        },
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    if r.ok:
        print(f"OK   {v}")
    else:
        msg = r.text.replace("\n", " ")[:160]
        print(f"FAIL {v}  {r.status_code} {msg}")
