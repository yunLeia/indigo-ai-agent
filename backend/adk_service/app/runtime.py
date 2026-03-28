from __future__ import annotations

import asyncio
import logging
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

# How often (in seconds) we ask the model "what do you hear?"
POLL_INTERVAL = 4.0


@dataclass
class ClassifiedFrame:
    """Output from Gemini Live: a classified audio event."""

    category: AudioCategory
    transcript: str
    confidence: float
    raw_text: str


class GeminiLiveRuntime:
    """
    Streams PCM16 audio to Gemini Live and periodically prompts it
    to classify what it hears. The model responds with audio (which we
    read via output_audio_transcription).
    """

    def __init__(self) -> None:
        self.api_key = settings.adk_gemini_api_key
        self.model = settings.gemini_live_model
        self.client = genai.Client(api_key=self.api_key)
        self._sessions: dict[str, object] = {}
        self._session_contexts: dict[str, object] = {}
        self._receive_tasks: dict[str, asyncio.Task[None]] = {}
        self._poll_tasks: dict[str, asyncio.Task[None]] = {}
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
            input_audio_transcription=types.AudioTranscriptionConfig(),
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
        self._poll_tasks[key] = asyncio.create_task(
            self._poll_loop(key, live_session)
        )

        log.info("[RUNTIME] Gemini Live session opened | user=%s", key)
        return live_session

    async def _poll_loop(
        self,
        key: str,
        live_session: object,
    ) -> None:
        """Periodically ask the model to classify what it's hearing."""
        await asyncio.sleep(POLL_INTERVAL)  # Initial delay to accumulate audio
        while True:
            try:
                log.debug("[RUNTIME] Polling Gemini: 'What do you hear right now?'")
                await live_session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text="What do you hear right now? Classify it.")],
                    ),
                    turn_complete=True,
                )
            except Exception as exc:
                log.warning("[RUNTIME] Poll send failed: %s", exc)
                return
            await asyncio.sleep(POLL_INTERVAL)

    async def _receive_loop(
        self,
        key: str,
        live_session: object,
    ) -> None:
        """Read responses from Gemini Live and parse classifications."""
        queue = self._queues[key]
        text_buffer = ""

        async for message in live_session.receive():
            sc = getattr(message, "server_content", None)
            if sc is None:
                continue

            # Log input transcription (what the mic picks up)
            it = getattr(sc, "input_transcription", None)
            if it and getattr(it, "text", None):
                log.info("[RUNTIME] Input transcription (mic) | user=%s | text=%r", key, it.text)

            # Collect output transcription (what the model says)
            ot = getattr(sc, "output_transcription", None)
            if ot and getattr(ot, "text", None):
                text_buffer += ot.text
                log.debug("[RUNTIME] Model speaking | user=%s | chunk=%r", key, ot.text)

            turn_complete = getattr(sc, "turn_complete", False)

            if turn_complete and text_buffer.strip():
                full_text = text_buffer.strip()
                text_buffer = ""

                log.info("[RUNTIME] Gemini full response | user=%s | text=%r", key, full_text)

                frame = _parse_keyword_response(full_text)
                if frame:
                    log.info(
                        "[RUNTIME] << Classified | category=%s | confidence=%.2f | transcript=%r",
                        frame.category,
                        frame.confidence,
                        frame.transcript[:100],
                    )
                    await queue.put(frame)
                else:
                    log.info("[RUNTIME] Response not actionable | text=%r", full_text[:200])
            elif turn_complete:
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

        if session.chunk_count % 100 == 0:
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

        for tasks in (self._poll_tasks, self._receive_tasks):
            task = tasks.pop(key, None)
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


# ── Ignore list: responses that mean "nothing interesting" ──
_IGNORE_PHRASES = [
    "i didn't hear",
    "i don't hear",
    "no sound",
    "silence",
    "nothing",
    "i can't hear",
    "ambient noise",
    "background noise",
    "quiet",
]


def _parse_keyword_response(text: str) -> Optional[ClassifiedFrame]:
    """
    Parse Gemini Live's spoken response. Expects "SIREN: ..." or "SPEECH: ...".
    Falls back to keyword detection if the model doesn't follow the prefix format.
    """
    lower = text.lower().strip()

    # Skip "I didn't hear anything" responses
    for phrase in _IGNORE_PHRASES:
        if phrase in lower:
            return None

    upper = text.upper().strip()

    # Check for keyword prefix
    if upper.startswith("SIREN"):
        transcript = text.split(":", 1)[1].strip() if ":" in text else text
        return ClassifiedFrame(
            category="SIREN",
            transcript=transcript,
            confidence=0.85,
            raw_text=text,
        )

    if upper.startswith("SPEECH"):
        transcript = text.split(":", 1)[1].strip() if ":" in text else text
        return ClassifiedFrame(
            category="SPEECH",
            transcript=transcript,
            confidence=0.85,
            raw_text=text,
        )

    # Fallback: check for siren-related keywords anywhere in the response
    siren_keywords = [
        "siren", "ambulance", "fire truck", "fire engine", "police",
        "emergency vehicle", "alarm", "fire alarm", "emergency",
        "horn", "wailing",
    ]
    for kw in siren_keywords:
        if kw in lower:
            return ClassifiedFrame(
                category="SIREN",
                transcript=text,
                confidence=0.7,
                raw_text=text,
            )

    # If it looks like transcribed speech (long enough, no "I hear" meta-description)
    if len(text.strip()) > 10 and "i hear" not in lower:
        return ClassifiedFrame(
            category="SPEECH",
            transcript=text,
            confidence=0.6,
            raw_text=text,
        )

    return None


def build_runtime() -> GeminiLiveRuntime:
    return GeminiLiveRuntime()
