"""Quick smoke check for the overlay logic. Not part of the formal test suite."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import apply_overlay, list_configs

base = {
    "query": {"text": "Q"},
    "answerGenerationSpec": {
        "includeCitations": True,
        "ignoreAdversarialQuery": True,
        "ignoreNonAnswerSeekingQuery": False,
    },
}

print("Available configs:", list_configs())

# 1. Baseline must be byte-identical to the original body.
baseline_body = apply_overlay(base, "baseline")
assert baseline_body == base, f"baseline overlay must be a no-op; got {baseline_body}"
print("PASS: baseline overlay is a no-op")

# 2. prompt-only adds preamble + ignoreLowRelevantContent (no search overrides
#    needed — the serving config's defaults already apply).
prompt_only_body = apply_overlay(base, "prompt-only")
assert "promptSpec" in prompt_only_body["answerGenerationSpec"]
assert prompt_only_body["answerGenerationSpec"]["ignoreLowRelevantContent"] is True
assert prompt_only_body["answerGenerationSpec"]["includeCitations"] is True  # base preserved
print("PASS: prompt-only adds preamble + ignoreLowRelevantContent; base preserved")

# 3. preview+prompt sets the `preview` modelVersion (server-rolled best
#    available; pro-* model versions are not accepted by the :answer API).
pro_body = apply_overlay(base, "preview+prompt")
assert pro_body["answerGenerationSpec"]["modelSpec"]["modelVersion"] == "preview"
print("PASS: preview+prompt sets modelVersion=preview")

# 4. kitchen-sink has all the bells (maxReturnResults capped at 25 by API).
ks = apply_overlay(base, "kitchen-sink")
assert ks["searchSpec"]["searchParams"]["maxReturnResults"] == 25
assert ks["queryUnderstandingSpec"]["queryRephraserSpec"]["maxRephraseSteps"] == 5
assert ks["groundingSpec"]["filteringLevel"] == "FILTERING_LEVEL_HIGH"
assert "Brand glossary" in ks["answerGenerationSpec"]["promptSpec"]["preamble"]
print("PASS: kitchen-sink has maxReturnResults=25, rephrase=5, grounding HIGH, brand glossary")

# 5. base dict must NOT have been mutated.
assert "modelSpec" not in base["answerGenerationSpec"]
assert "searchSpec" not in base
print("PASS: base dict not mutated by overlay")

print("\n--- Sample request body for kitchen-sink (truncated) ---")
out = json.dumps(ks, indent=2)
print(out[:1200] + ("\n... [truncated]" if len(out) > 1200 else ""))
