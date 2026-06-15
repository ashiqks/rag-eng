"""Loads engine config from tests/eval/.env so we have one source of truth."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = REPO_ROOT / "tests" / "eval" / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)


@dataclass(frozen=True)
class Settings:
    project_id: str
    location: str
    engine_id: str
    serving_config: str
    collection: str
    host: str = "https://discoveryengine.googleapis.com"
    api_version: str = "v1"

    @property
    def base_url(self) -> str:
        return (
            f"{self.host}/{self.api_version}"
            f"/projects/{self.project_id}"
            f"/locations/{self.location}"
            f"/collections/{self.collection}"
            f"/engines/{self.engine_id}"
        )

    def session_path(self, session_id: str) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/collections/{self.collection}/engines/{self.engine_id}"
            f"/sessions/{session_id}"
        )


def _required(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(
            f"{key} not set. Expected in {ENV_PATH} or environment. "
            f"See tests/eval/.env.example for the full list."
        )
    return val


settings = Settings(
    project_id=_required("SEARCH_PROJECT_ID"),
    location=_required("SEARCH_LOCATION"),
    engine_id=_required("SEARCH_ENGINE_ID"),
    serving_config=os.environ.get("SEARCH_SERVING_CONFIG", "default_search"),
    collection=os.environ.get("SEARCH_COLLECTION", "default_collection"),
)
