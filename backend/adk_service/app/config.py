from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env_files() -> None:
    current = Path(__file__).resolve()
    candidates = [
        current.parents[1] / ".env.local",
        current.parents[1] / ".env",
        current.parents[3] / ".env.local",
        current.parents[3] / ".env",
    ]

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            load_dotenv(candidate, override=False)


_load_env_files()


class ServiceSettings:
    def __init__(self) -> None:
        self.next_pipeline_url = os.getenv(
            "NEXT_PIPELINE_URL",
            "http://localhost:3000/api/live/ingest",
        )
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.adk_agent_model = os.getenv("ADK_AGENT_MODEL", self.gemini_model)
        # ADK infers the app name from its installed package layout in our current
        # local setup, so we keep this configurable instead of hardcoding it.
        self.adk_app_name = os.getenv("ADK_APP_NAME", "agents")
        self.demo_mode = os.getenv("ADK_SERVICE_DEMO_MODE", "true").lower() == "true"
        self.orchestration_mode = os.getenv(
            "ADK_ORCHESTRATION_MODE",
            "bridge",
        )
        self.audio_input_mode = os.getenv(
            "ADK_AUDIO_INPUT_MODE",
            "browser-webm",
        )


settings = ServiceSettings()
