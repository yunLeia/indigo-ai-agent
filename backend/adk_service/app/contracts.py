from __future__ import annotations

from typing import Literal, Optional, TypedDict, Union

from pydantic import BaseModel


AudioCategory = Literal["SIREN", "SPEECH", "AMBIENT"]


class InitMessage(BaseModel):
    model_config = {"extra": "ignore"}
    type: Literal["init"]
    user_name: str
    user_id: str


class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"]
    data: str
    format: Literal["browser-webm", "pcm16"] = "pcm16"
    sample_rate_hz: Optional[int] = None


class SoundDetectedEvent(TypedDict):
    type: Literal["sound_detected"]
    text: str
    latency_ms: int


class AgentUpdateEvent(TypedDict):
    type: Literal["agent_update"]
    agent: str
    status: Literal["active", "done"]
    output: str


class AlertEvent(TypedDict):
    type: Literal["alert"]
    scenario: Literal["siren", "name"]
    title: str
    subtitle: str
    risk: str


ServerEvent = Union[SoundDetectedEvent, AgentUpdateEvent, AlertEvent]
