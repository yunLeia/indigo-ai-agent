from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioSession:
    user_name: str
    user_id: str
    chunk_count: int = 0
    live_session_key: Optional[str] = None

    def register_chunk(self) -> None:
        self.chunk_count += 1
