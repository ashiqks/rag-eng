"""Named search/answer configurations for the Discovery Engine `:answer` API.

Each entry in CONFIGS is a deep-mergeable overlay for the request body sent
by run_eval.ask(). `baseline` reproduces the historical (default) request
shape exactly; the other presets layer on a strict anti-hallucination
preamble, model upgrades, broader retrieval, and grounding strictness.

To add a new preset, copy an existing entry and override only the keys you
need. The runner will deep-merge `request_overlay` into the default body.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


# ---------------------------------------------------------------------------
# Preambles
# ---------------------------------------------------------------------------

PREAMBLE_STRICT = (
    "You are an analyst answering questions strictly from the provided "
    "documents. Hard rules:\n"
    "1. Never invent dates, numbers, percentages, test names, brand codes, "
    "or document titles. If a fact is not stated verbatim in the retrieved "
    "chunks, omit it.\n"
    "2. When referring to a test, use the exact name as it appears in the "
    "chunk. If no name appears, refer to it descriptively (e.g., 'a 2025 "
    "Old Navy PDP test') without inventing a title.\n"
    "3. When the chunk filename encodes the year (e.g., '2018_...'), you "
    "MAY cite that year, but only if the chunk's textual content also "
    "discusses dates consistent with it.\n"
    "4. Quantitative claims (RPV, OPV, return-rate %, engagement %) must "
    "be quoted from the chunk verbatim or omitted.\n"
    "5. If the retrieved chunks do not answer the question, say so "
    "explicitly rather than guessing."
)

PREAMBLE_STRICT_WITH_GLOSSARY = (
    PREAMBLE_STRICT
    + "\n\nBrand glossary (use only when the chunk uses these codes):\n"
    "- ON = Old Navy. GAP = Gap. BR = Banana Republic. AT = Athleta.\n"
    "- BRONGA = a multi-brand banner. BRFGF = BR Factory.\n"
    "- ATB = Add-To-Bag. PDP = Product Detail Page. PLP = Product List Page.\n"
    "- KPI deltas reported as '+X% on RPV' refer to revenue-per-visit.\n"
    "Do NOT expand or interpret an acronym not in this list; quote it as it "
    "appears."
)


# ---------------------------------------------------------------------------
# Configs
# ---------------------------------------------------------------------------

CONFIGS: dict[str, dict[str, Any]] = {
    "baseline": {
        "description": (
            "Historical default. No model selection, no preamble, no "
            "search overrides. Reproduces today's results."
        ),
        "model_label": "default",
        "request_overlay": {},
    },
    "prompt-only": {
        "description": (
            "Adds the strict anti-hallucination preamble + "
            "ignoreLowRelevantContent. Same default model and retrieval. "
            "Isolates the prompt impact."
        ),
        "model_label": "default",
        "request_overlay": {
            "answerGenerationSpec": {
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
        },
    },
    "flash-2.5+prompt": {
        "description": (
            "Strict preamble + gemini-2.5-flash answer generator. Cheap upgrade."
        ),
        "model_label": "gemini-2.5-flash",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "gemini-2.5-flash/answer_gen/v1"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
        },
    },
    "preview+prompt": {
        "description": (
            "Strict preamble + the server-rolled `preview` answer generator "
            "(latest model Discovery Engine has enabled for :answer). "
            "Best instruction-following available; default retrieval."
        ),
        "model_label": "preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "preview"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
        },
    },
    "preview+recall": {
        "description": (
            "preview+prompt with maxReturnResults=25 and 3-step query "
            "rephrasing. Targets context_recall failures on broad questions."
        ),
        "model_label": "preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "preview"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
            "searchSpec": {
                "searchParams": {"maxReturnResults": 25},
            },
            "queryUnderstandingSpec": {
                "queryRephraserSpec": {"maxRephraseSteps": 3},
            },
        },
    },
    "preview+grounding": {
        "description": (
            "preview+recall with groundingSpec.filteringLevel=HIGH. "
            "Server-side abstention on unsupported claims."
        ),
        "model_label": "preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "preview"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
            "searchSpec": {
                "searchParams": {"maxReturnResults": 25},
            },
            "queryUnderstandingSpec": {
                "queryRephraserSpec": {"maxRephraseSteps": 3},
            },
            "groundingSpec": {"filteringLevel": "FILTERING_LEVEL_HIGH"},
        },
    },
    "kitchen-sink": {
        "description": (
            "Upper-bound config: preview model + brand-glossary preamble + "
            "maxReturnResults=25 (API cap) + 5-step rephrase + grounding HIGH."
        ),
        "model_label": "preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "preview"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT_WITH_GLOSSARY},
            },
            "searchSpec": {
                "searchParams": {"maxReturnResults": 25},
            },
            "queryUnderstandingSpec": {
                "queryRephraserSpec": {"maxRephraseSteps": 5},
            },
            "groundingSpec": {"filteringLevel": "FILTERING_LEVEL_HIGH"},
        },
    },
    "gemini-3.1-pro+prompt": {
        "description": (
            "Strict preamble + gemini-3.1-pro-preview answer generator "
            "(probed accepted by the :answer API). Default retrieval."
        ),
        "model_label": "gemini-3.1-pro-preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "gemini-3.1-pro-preview/answer_gen/v1"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
        },
    },
    "gemini-3.1-pro+recall": {
        "description": (
            "gemini-3.1-pro+prompt with maxReturnResults=25 and 3-step "
            "query rephrasing. Pro 3.1 with broader retrieval."
        ),
        "model_label": "gemini-3.1-pro-preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "gemini-3.1-pro-preview/answer_gen/v1"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
            "searchSpec": {
                "searchParams": {"maxReturnResults": 25},
            },
            "queryUnderstandingSpec": {
                "queryRephraserSpec": {"maxRephraseSteps": 3},
            },
        },
    },
    "gemini-3.1-pro+grounding": {
        "description": (
            "gemini-3.1-pro+recall with groundingSpec.filteringLevel=HIGH. "
            "Pro 3.1 + server-side abstention on unsupported claims."
        ),
        "model_label": "gemini-3.1-pro-preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "gemini-3.1-pro-preview/answer_gen/v1"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT},
            },
            "searchSpec": {
                "searchParams": {"maxReturnResults": 25},
            },
            "queryUnderstandingSpec": {
                "queryRephraserSpec": {"maxRephraseSteps": 3},
            },
            "groundingSpec": {"filteringLevel": "FILTERING_LEVEL_HIGH"},
        },
    },
    "gemini-3.1-pro+glossary": {
        "description": (
            "gemini-3.1-pro+prompt with the brand-glossary preamble. "
            "Tests whether the glossary helps Pro 3.1 disambiguate brand codes."
        ),
        "model_label": "gemini-3.1-pro-preview",
        "request_overlay": {
            "answerGenerationSpec": {
                "modelSpec": {"modelVersion": "gemini-3.1-pro-preview/answer_gen/v1"},
                "ignoreLowRelevantContent": True,
                "promptSpec": {"preamble": PREAMBLE_STRICT_WITH_GLOSSARY},
            },
        },
    },
}


def list_configs() -> list[str]:
    return list(CONFIGS.keys())


def get_config(name: str) -> dict[str, Any]:
    if name not in CONFIGS:
        raise KeyError(
            f"Unknown config '{name}'. Available: {list_configs()}"
        )
    return CONFIGS[name]


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge `overlay` into a copy of `base`. Overlay wins on conflict."""
    out = deepcopy(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def apply_overlay(base_body: dict[str, Any], config_name: str) -> dict[str, Any]:
    overlay = get_config(config_name)["request_overlay"]
    return deep_merge(base_body, overlay)
