from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types

from app.audio_codec import build_audio_decoder
from app.config import settings
from app.contracts import AudioCategory, AudioChunkMessage
from app.prompts import GEMINI_LIVE_SYSTEM_INSTRUCTION
from app.session import AudioSession

log = logging.getLogger("myindigo.runtime")


@dataclass
class ClassifiedFrame:
    """Output from Gemini Live: a classified audio event."""

    category: AudioCategory
    transcript: str
    confidence: float
    raw_text: str


class GeminiLiveRuntime:
    """
    Streams PCM16 audio to Gemini Live and receives JSON classifications.
    Gemini Live is the "ears" — it hears audio and outputs structured JSON
    with category (SIREN/SPEECH/AMBIENT), transcript, and confidence.
    """

    def __init__(self) -> None:
        self.api_key = settings.adk_gemini_api_key
        self.model = settings.gemini_live_model
        self.client = genai.Client(api_key=self.api_key)
        self._sessions: dict[str, object] = {}
        self._session_contexts: dict[str, object] = {}
        self._receive_tasks: dict[str, asyncio.Task[None]] = {}
        self._queues: dict[str, asyncio.Queue[ClassifiedFrame]] = {}

        log.info(
            "[RUNTIME] GeminiLiveRuntime initialized | model=%s | key_present=%s",
            self.model,
            bool(self.api_key),
        )

    async def _ensure_session(self, session: AudioSession) -> object:
        key = session.user_id
        if key in self._sessions:
            return self._sessions[key]

        log.info(
            "[RUNTIME] Opening Gemini Live session | user=%s | model=%s",
            key,
            self.model,
        )

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=GEMINI_LIVE_SYSTEM_INSTRUCTION,
        )

        live_context = self.client.aio.live.connect(
            model=self.model,
            config=config,
        )
        live_session = await live_context.__aenter__()
        session.live_session_key = key
        self._sessions[key] = live_session
        self._session_contexts[key] = live_context
        self._queues[key] = asyncio.Queue()
        self._receive_tasks[key] = asyncio.create_task(
            self._receive_loop(key, live_session)
        )

        log.info("[RUNTIME] Gemini Live session opened | user=%s", key)
        return live_session

    async def _receive_loop(
        self,
        key: str,
        live_session: object,
    ) -> None:
        """Read responses from Gemini Live and parse JSON classifications."""
        queue = self._queues[key]
        text_buffer = ""

        async for message in live_session.receive():
            # native-audio model returns audio + transcription
            # We read the output_transcription to get text
            sc = getattr(message, "server_content", None)
            if sc is None:
                continue

            # Check output_transcription (streamed text from audio response)
            ot = getattr(sc, "output_transcription", None)
            if ot and getattr(ot, "text", None):
                text_buffer += ot.text
                log.debug("[RUNTIME] Gemini Live transcription chunk | user=%s | text=%r", key, ot.text)

            # Also check turn_complete to flush buffer
            turn_complete = getattr(sc, "turn_complete", False)

            # Try to parse complete JSON objects from the buffer
            frames = _extract_json_frames(text_buffer)
            for frame, consumed in frames:
                text_buffer = text_buffer[consumed:]
                log.info(
                    "[RUNTIME] << Gemini Live classified | category=%s | confidence=%.2f | transcript=%r",
                    frame.category,
                    frame.confidence,
                    frame.transcript[:100],
                )
                await queue.put(frame)

            # On turn complete, if there's leftover text that didn't parse as JSON,
            # log it so we can debug prompt issues
            if turn_complete and text_buffer.strip():
                log.warning(
                    "[RUNTIME] Unparsed text at turn end | user=%s | text=%r",
                    key,
                    text_buffer.strip()[:200],
                )
                text_buffer = ""

    async def ingest_audio(
        self,
        session: AudioSession,
        chunk: AudioChunkMessage,
    ) -> Optional[ClassifiedFrame]:
        """Send an audio chunk to Gemini Live. Returns a frame if one is ready."""
        decoded = build_audio_decoder(chunk).decode(chunk)

        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY for GeminiLiveRuntime.")

        live_session = await self._ensure_session(session)
        await live_session.send_realtime_input(
            media=types.Blob(
                data=decoded.raw_bytes,
                mime_type=decoded.mime_type,
            )
        )
        session.register_chunk()

        if session.chunk_count % 50 == 0:
            log.debug(
                "[RUNTIME] Audio chunks sent | user=%s | total=%d",
                session.user_id,
                session.chunk_count,
            )

        # Check if Gemini has produced a classification
        queue = self._queues[session.user_id]
        try:
            frame = await asyncio.wait_for(queue.get(), timeout=0.1)
            return frame
        except (TimeoutError, asyncio.TimeoutError):
            return None

    async def close_session(self, session: AudioSession) -> None:
        key = session.live_session_key or session.user_id
        log.info("[RUNTIME] Closing Gemini Live session | user=%s", key)

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


def _extract_json_frames(text: str) -> list[tuple[ClassifiedFrame, int]]:
    """
    Extract JSON objects from text buffer. Returns list of (frame, chars_consumed).
    Handles Gemini sometimes wrapping JSON in markdown or adding extra text.
    """
    results: list[tuple[ClassifiedFrame, int]] = []

    # Find all JSON-like objects in the text
    for match in re.finditer(r"\{[^{}]*\}", text):
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue

        category = data.get("category", "").upper()
        if category not in ("SIREN", "SPEECH", "AMBIENT"):
            continue

        frame = ClassifiedFrame(
            category=category,
            transcript=data.get("transcript", ""),
            confidence=float(data.get("confidence", 0.5)),
            raw_text=match.group(0),
        )
        results.append((frame, match.end()))

    return results


def build_runtime() -> GeminiLiveRuntime:
    return GeminiLiveRuntime()
