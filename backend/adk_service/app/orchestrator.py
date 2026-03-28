from __future__ import annotations

from typing import Any, Optional

from app.adk_runner import run_adk_reasoning
from app.config import settings
from app.contracts import OrchestrationMode, ScenarioName, ServerEvent
from app.pipeline_bridge import map_pipeline_to_events, run_existing_pipeline


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

            result = await run_existing_pipeline(
                transcript=transcript,
                confidence=confidence,
                scenario=scenario,
            )
            result["_fallback"] = {
                "mode": "bridge",
                "reason": str(exc),
            }
            events = map_pipeline_to_events(result, scenario)
            return result, events

    result = await run_existing_pipeline(
        transcript=transcript,
        confidence=confidence,
        scenario=scenario,
    )
    events = map_pipeline_to_events(result, scenario)
    return result, events
