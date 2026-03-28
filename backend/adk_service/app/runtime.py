from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

from app.audio_codec import build_audio_decoder
from app.config import settings
from app.contracts import AudioChunkMessage, ScenarioName
from app.session import AudioSession


@dataclass
class TranscriptFrame:
    text: str
    confidence: float
    is_final: bool
    scenario: ScenarioName


class BaseRealtimeRuntime:
    async def ingest_audio(
        self,
        session: AudioSession,
        _chunk: AudioChunkMessage,
    ) -> Optional[TranscriptFrame]:
        raise NotImplementedError

    async def close_session(self, _session: AudioSession) -> None:
        return None

    async def shutdown(self) -> None:
        return None


class DemoTranscriptRuntime(BaseRealtimeRuntime):
    DEMO_TRANSCRIPTS = {
        "siren": "I can hear a siren and a fire truck is approaching from behind.",
        "hospital": "Alex Kim, please proceed to Exam Room 3 now.",
    }

    async def ingest_audio(
        self,
        session: AudioSession,
        chunk: AudioChunkMessage,
    ) -> Optional[TranscriptFrame]:
        build_audio_decoder(chunk).decode(chunk)
        session.register_chunk()
        if not session.ready_for_demo_final:
            return None

        session.final_text = self.DEMO_TRANSCRIPTS[session.scenario]
        return TranscriptFrame(
            text=session.final_text,
            confidence=0.96 if session.scenario == "siren" else 0.91,
            is_final=True,
            scenario=session.scenario,
        )


class GeminiLiveRuntime(BaseRealtimeRuntime):
    """
    Placeholder runtime for the real Gemini Live streaming path.

    Planned implementation:
    - decode browser audio chunks into the format expected by Gemini Live
    - maintain a persistent session per websocket client
    - emit partial frames and final transcript frames
    - optionally route transcript text to ADK specialist agents
    """

    def __init__(self) -> None:
        self.api_key = settings.adk_gemini_api_key
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=self.api_key)
        self._sessions: dict[str, object] = {}
        self._session_contexts: dict[str, object] = {}
        self._receive_tasks: dict[str, asyncio.Task[None]] = {}
        self._queues: dict[str, asyncio.Queue[TranscriptFrame]] = {}

    async def _ensure_session(self, session: AudioSession) -> object:
        key = session.user_id
        if key in self._sessions:
            return self._sessions[key]

        live_context = self.client.aio.live.connect(
            model=self.model,
            config={
                "response_modalities": ["TEXT"],
            },
        )
        live_session = await live_context.__aenter__()
        session.live_session_key = key
        self._sessions[key] = live_session
        self._session_contexts[key] = live_context
        self._queues[key] = asyncio.Queue()
        self._receive_tasks[key] = asyncio.create_task(
            self._receive_loop(key, live_session, session.scenario)
        )
        return live_session

    async def _receive_loop(
        self,
        key: str,
        live_session: object,
        scenario: ScenarioName,
    ) -> None:
        queue = self._queues[key]
        async for message in live_session.receive():
            text = getattr(message, "text", None)
            if not text:
                continue

            await queue.put(
                TranscriptFrame(
                    text=text,
                    confidence=0.9,
                    is_final=True,
                    scenario=scenario,
                )
            )

    async def ingest_audio(
        self,
        session: AudioSession,
        chunk: AudioChunkMessage,
    ) -> Optional[TranscriptFrame]:
        decoded = build_audio_decoder(chunk).decode(chunk)

        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY for GeminiLiveRuntime.")

        if decoded.mime_type != "audio/pcm;rate=16000":
            raise RuntimeError(
                "Gemini Live runtime expects PCM16 audio. "
                "Send audio chunks with format=pcm16 and sample_rate_hz=16000, "
                "or keep browser-webm for demo mode only."
            )

        live_session = await self._ensure_session(session)
        await live_session.send_realtime_input(
            media=types.Blob(
                data=decoded.raw_bytes,
                mime_type=decoded.mime_type,
            )
        )

        queue = self._queues[session.user_id]
        try:
            frame = await asyncio.wait_for(queue.get(), timeout=0.15)
            session.final_text = frame.text
            return frame
        except TimeoutError:
            return None

    async def close_session(self, session: AudioSession) -> None:
        key = session.live_session_key or session.user_id

        task = self._receive_tasks.pop(key, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        live_session = self._sessions.pop(key, None)
        if live_session is not None:
            await live_session.close()

        live_context = self._session_contexts.pop(key, None)
        if live_context is not None:
            await live_context.__aexit__(None, None, None)

        self._queues.pop(key, None)

    async def shutdown(self) -> None:
        keys = list(self._sessions.keys())
        for key in keys:
            await self.close_session(
                AudioSession(user_name=key, user_id=key, live_session_key=key)
            )
        await self.client.aio.aclose()


def build_runtime() -> BaseRealtimeRuntime:
    if settings.demo_mode:
        return DemoTranscriptRuntime()

    return GeminiLiveRuntime()
