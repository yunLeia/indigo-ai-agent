from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.adk_runner import run_adk_reasoning
from app.config import settings
from app.contracts import OrchestrationMode, ScenarioName, ServerEvent
from app.pipeline_bridge import map_pipeline_to_events, run_existing_pipeline

_ADK_BACKOFF_UNTIL: Optional[datetime] = None


def _current_utc() -> datetime:
    return datetime.now(timezone.utc)


def _seconds_until_backoff_expires() -> int:
    if _ADK_BACKOFF_UNTIL is None:
        return 0

    remaining = (_ADK_BACKOFF_UNTIL - _current_utc()).total_seconds()
    return max(0, int(remaining))


def _parse_retry_after_seconds(message: str) -> Optional[int]:
    retry_patterns = [
        r"retryDelay': '(\d+)s'",
        r"retry in ([0-9]+(?:\.[0-9]+)?)s",
        r"Please retry in ([0-9]+(?:\.[0-9]+)?)s",
    ]
    for pattern in retry_patterns:
        match = re.search(pattern, message)
        if match:
            return max(1, int(float(match.group(1))))
    return None


def _build_fallback_metadata(
    *,
    reason: str,
    kind: str,
    retry_after_seconds: Optional[int] = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "mode": "bridge",
        "kind": kind,
        "reason": reason,
        "at": _current_utc().isoformat(),
    }
    if retry_after_seconds:
        metadata["retry_after_seconds"] = retry_after_seconds
    return metadata


def _classify_adk_error(exc: Exception) -> dict[str, Any]:
    reason = str(exc)
    lowered = reason.lower()
    retry_after_seconds = _parse_retry_after_seconds(reason)

    if "resource_exhausted" in lowered or "quota exceeded" in lowered:
        return _build_fallback_metadata(
            reason=reason,
            kind="quota_exhausted",
            retry_after_seconds=retry_after_seconds,
        )

    if "api key" in lowered or "permission_denied" in lowered:
        return _build_fallback_metadata(reason=reason, kind="credentials")

    return _build_fallback_metadata(
        reason=reason,
        kind="adk_error",
        retry_after_seconds=retry_after_seconds,
    )


def get_adk_runtime_status() -> dict[str, Any]:
    remaining_seconds = _seconds_until_backoff_expires()
    return {
        "backoff_active": remaining_seconds > 0,
        "backoff_remaining_seconds": remaining_seconds,
    }


async def run_orchestration(
    *,
    transcript: str,
    confidence: float,
    scenario: ScenarioName,
    user_name: str,
    mode_override: Optional[OrchestrationMode] = None,
) -> tuple[dict[str, Any], list[ServerEvent]]:
    mode = mode_override or settings.orchestration_mode

    if mode == "adk":
        backoff_remaining = _seconds_until_backoff_expires()
        if backoff_remaining > 0:
            result = await run_existing_pipeline(
                transcript=transcript,
                confidence=confidence,
                scenario=scenario,
            )
            result["_fallback"] = _build_fallback_metadata(
                reason="ADK is temporarily cooling down after a quota error.",
                kind="adk_cooldown",
                retry_after_seconds=backoff_remaining,
            )
            events = map_pipeline_to_events(result, scenario)
            return result, events

        try:
            result = await run_adk_reasoning(
                transcript=transcript,
                scenario=scenario,
                user_name=user_name,
            )
            events = map_pipeline_to_events(result, scenario)
            return result, events
        except Exception as exc:
            if not settings.demo_mode:
                raise

            fallback = _classify_adk_error(exc)
            retry_after_seconds = fallback.get("retry_after_seconds")
            if retry_after_seconds:
                global _ADK_BACKOFF_UNTIL
                _ADK_BACKOFF_UNTIL = _current_utc() + timedelta(
                    seconds=retry_after_seconds
                )

            result = await run_existing_pipeline(
                transcript=transcript,
                confidence=confidence,
                scenario=scenario,
            )
            result["_fallback"] = fallback
            events = map_pipeline_to_events(result, scenario)
            return result, events

    result = await run_existing_pipeline(
        transcript=transcript,
        confidence=confidence,
        scenario=scenario,
    )
    events = map_pipeline_to_events(result, scenario)
    return result, events
