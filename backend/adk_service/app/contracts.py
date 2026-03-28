from __future__ import annotations

from typing import Literal, Optional, TypedDict, Union

from pydantic import BaseModel


ScenarioName = Literal["siren", "hospital"]
OrchestrationMode = Literal["bridge", "adk"]


class InitMessage(BaseModel):
    type: Literal["init"]
    user_name: str
    user_id: str
    scenario: Optional[ScenarioName] = None


class AudioChunkMessage(BaseModel):
    type: Literal["audio_chunk"]
    data: str
    format: Literal["browser-webm", "pcm16"] = "browser-webm"
    sample_rate_hz: Optional[int] = None


class DebugOrchestrateRequest(BaseModel):
    transcript: str
    scenario: ScenarioName
    user_name: str = "Alex Kim"
    confidence: float = 0.9
    mode: Optional[OrchestrationMode] = None


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
