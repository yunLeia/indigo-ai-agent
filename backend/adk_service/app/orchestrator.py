from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.adk_runner import run_agent
from app.config import settings
from app.contracts import AudioCategory, ServerEvent
from app.runtime import ClassifiedFrame

log = logging.getLogger("myindigo.orchestrator")

# Debounce: don't fire the same scenario twice within this window
DEBOUNCE_SECONDS = 8
_last_alert: dict[str, float] = {}


def _name_matches(transcript: str, user_name: str) -> bool:
    """Fast rule-based check: does the transcript contain the user's name?"""
    t = transcript.lower()
    full = user_name.lower().strip()
    first = full.split()[0] if full else ""
    return full in t or (len(first) >= 2 and first in t)


async def dispatch_and_run(
    *,
    frame: ClassifiedFrame,
    user_name: str,
    send_event: Any,
) -> None:
    """
    Rule-based dispatch + ADK agent execution.

    1. Look at Gemini Live's classification (SIREN/SPEECH/AMBIENT)
    2. Route to the right ADK agent (or drop)
    3. Send WebSocket events as the pipeline progresses
    """
    category = frame.category
    transcript = frame.transcript
    confidence = frame.confidence

    log.info(
        "[DISPATCH] Received frame | category=%s | confidence=%.2f | transcript=%r",
        category,
        confidence,
        transcript[:100],
    )

    # ── Gate: confidence threshold ──
    if confidence < settings.confidence_threshold:
        log.info(
            "[DISPATCH] Dropped (low confidence %.2f < %.2f)",
            confidence,
            settings.confidence_threshold,
        )
        return

    # ── Gate: AMBIENT → drop ──
    if category == "AMBIENT":
        log.info("[DISPATCH] Dropped AMBIENT")
        return

    # ── Route: SIREN → SirenAgent ──
    if category == "SIREN":
        # Debounce
        now = time.time()
        if now - _last_alert.get("siren", 0) < DEBOUNCE_SECONDS:
            log.info("[DISPATCH] Debounced siren (within %ds window)", DEBOUNCE_SECONDS)
            return

        log.info("[DISPATCH] Routing to SirenAgent")
        await send_event({
            "type": "sound_detected",
            "text": transcript or "Emergency sound detected",
            "latency_ms": 0,
        })
        await send_event({
            "type": "agent_update",
            "agent": "dispatch",
            "status": "done",
            "output": f"Emergency sound detected (confidence: {confidence:.0%}) → SirenAgent",
        })
        await send_event({
            "type": "agent_update",
            "agent": "siren",
            "status": "active",
            "output": "Analyzing emergency sound...",
        })

        try:
            result = await run_agent(
                agent_name="siren",
                transcript=transcript,
                user_name=user_name,
            )
        except Exception as exc:
            log.error("[DISPATCH] SirenAgent failed: %s", exc)
            await send_event({
                "type": "agent_update",
                "agent": "siren",
                "status": "done",
                "output": f"Error: {exc}",
            })
            return

        confirmed = result.get("confirmed", False)
        await send_event({
            "type": "agent_update",
            "agent": "siren",
            "status": "done",
            "output": result.get("reason", "Analysis complete"),
        })

        if confirmed:
            _last_alert["siren"] = now
            log.info(
                "[DISPATCH] SirenAgent CONFIRMED | risk=%s | title=%r",
                result.get("risk"),
                result.get("title"),
            )
            await send_event({
                "type": "alert",
                "scenario": "siren",
                "title": result.get("title", "Emergency sound detected"),
                "subtitle": result.get("subtitle", "Check your surroundings"),
                "risk": result.get("risk", "HIGH"),
            })
        else:
            log.info(
                "[DISPATCH] SirenAgent REJECTED | reason=%r",
                result.get("reason"),
            )
        return

    # ── Route: SPEECH → check name → NameAgent ──
    if category == "SPEECH":
        if not transcript:
            log.info("[DISPATCH] Dropped SPEECH (empty transcript)")
            return

        has_name = _name_matches(transcript, user_name)
        log.info(
            "[DISPATCH] SPEECH received | name_match=%s | user_name=%r",
            has_name,
            user_name,
        )

        if not has_name:
            log.info("[DISPATCH] Dropped SPEECH (name not found in transcript)")
            return

        # Debounce
        now = time.time()
        if now - _last_alert.get("name", 0) < DEBOUNCE_SECONDS:
            log.info("[DISPATCH] Debounced name (within %ds window)", DEBOUNCE_SECONDS)
            return

        log.info("[DISPATCH] Name matched → routing to NameAgent")
        await send_event({
            "type": "sound_detected",
            "text": f"Speech detected: \"{transcript[:60]}...\"" if len(transcript) > 60 else f"Speech detected: \"{transcript}\"",
            "latency_ms": 0,
        })
        await send_event({
            "type": "agent_update",
            "agent": "dispatch",
            "status": "done",
            "output": f"Name '{user_name}' found in speech → NameAgent",
        })
        await send_event({
            "type": "agent_update",
            "agent": "name",
            "status": "active",
            "output": "Analyzing announcement...",
        })

        try:
            result = await run_agent(
                agent_name="name",
                transcript=transcript,
                user_name=user_name,
            )
        except Exception as exc:
            log.error("[DISPATCH] NameAgent failed: %s", exc)
            await send_event({
                "type": "agent_update",
                "agent": "name",
                "status": "done",
                "output": f"Error: {exc}",
            })
            return

        confirmed = result.get("confirmed", False)
        await send_event({
            "type": "agent_update",
            "agent": "name",
            "status": "done",
            "output": result.get("reason", "Analysis complete"),
        })

        if confirmed:
            _last_alert["name"] = now
            log.info(
                "[DISPATCH] NameAgent CONFIRMED | title=%r | location=%r",
                result.get("title"),
                result.get("location_detail"),
            )
            await send_event({
                "type": "alert",
                "scenario": "name",
                "title": result.get("title", "Your name was called"),
                "subtitle": result.get("subtitle", "Check the announcement"),
                "risk": "MEDIUM",
            })
        else:
            log.info(
                "[DISPATCH] NameAgent REJECTED | reason=%r",
                result.get("reason"),
            )
        return
