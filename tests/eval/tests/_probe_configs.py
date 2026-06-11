"""Live probe: send one request per challenger config to surface API errors fast."""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from run_eval import ask, build_answer_url, extract_answer_and_context, get_access_token  # noqa: E402
from configs import list_configs  # noqa: E402

cfg = argparse.Namespace(
    search_project_id=os.environ["SEARCH_PROJECT_ID"],
    search_location=os.environ.get("SEARCH_LOCATION", "global"),
    search_collection=os.environ.get("SEARCH_COLLECTION", "default_collection"),
    search_engine_id=os.environ["SEARCH_ENGINE_ID"],
    search_serving_config=os.environ.get("SEARCH_SERVING_CONFIG", "default_search"),
)
url = build_answer_url(cfg)
tok = get_access_token()
question = "Have we tested anything similar to a checkout simplification before?"

names = sys.argv[1:] or list_configs()
for name in names:
    try:
        r = ask(url, tok, cfg.search_project_id, question, name)
        ans, ctx, cit = extract_answer_and_context(r["resp"])
        print(f"{name}: OK  latency={r['latency_ms']}ms ans_len={len(ans)} ctx_chunks={len(ctx)}")
    except Exception as e:
        print(f"{name}: FAIL  {str(e)[:300]}")
