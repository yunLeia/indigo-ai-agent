from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.contracts import ScenarioName


@dataclass
class AudioSession:
    user_name: str
    user_id: str
    scenario: ScenarioName = "siren"
    chunk_count: int = 0
    partial_text: Optional[str] = None
    final_text: Optional[str] = None
    notes: list[str] = field(default_factory=list)
    live_session_key: Optional[str] = None

    def register_chunk(self) -> None:
        self.chunk_count += 1

    @property
    def ready_for_demo_final(self) -> bool:
        return self.chunk_count >= 3 and self.final_text is None
