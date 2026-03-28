from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.context_payloads import build_raw_context
from app.contracts import ScenarioName, ServerEvent


def _build_local_demo_result(
    *,
    transcript: str,
    confidence: float,
    scenario: ScenarioName,
) -> dict[str, Any]:
    is_siren = scenario == "siren"
    title = (
        "Emergency vehicle approaching"
        if is_siren
        else "Your name was called"
    )
    body = (
        "Move right and yield immediately."
        if is_siren
        else "Go to Exam Room 3 now."
    )
    signal = "emergency_vehicle_siren" if is_siren else "hospital_pa"

    return {
        "rawContext": build_raw_context(scenario),
        "context": {
            "scenarioLabel": "Emergency vehicle outdoors"
            if is_siren
            else "Hospital public announcement",
            "locationLabel": "Chelsea, NYC" if is_siren else "NYU Langone lobby",
            "environmentLabel": "street" if is_siren else "hospital",
            "userSituation": "on_foot" if is_siren else "waiting_room",
        },
        "observation": {
            "transcript": transcript,
            "detectedSignal": signal,
            "confidence": confidence,
            "timestampIso": "2026-03-27T00:00:00Z",
            "source": "microphone",
        },
        "dispatch": {
            "category": "emergency" if is_siren else "info",
            "signal": signal,
            "confidence": confidence,
            "routeTo": "architect",
            "reasoning": (
                "Rule-based demo fallback classified an emergency vehicle siren."
                if is_siren
                else "Rule-based demo fallback classified a hospital PA announcement."
            ),
        },
        "architect": {
            "mode": "emergency" if is_siren else "info",
            "severity": "high" if is_siren else "medium",
            "title": title,
            "userMessage": body,
            "recommendedActions": (
                ["Move right", "Check surroundings", "Yield immediately"]
                if is_siren
                else ["Read summary", "Go to Exam Room 3"]
            ),
            "wearableSignal": "strong-vibration"
            if is_siren
            else "standard-vibration",
            "escalation": "notify-now" if is_siren else "surface-now",
        },
        "executor": {
            "channel": "phone-and-wearable",
            "phoneTitle": title,
            "phoneBody": body,
            "wearableTitle": title,
            "wearableBody": body,
            "vibration": "strong" if is_siren else "standard",
            "actions": (
                [
                    {"id": "open-map", "label": "Show map"},
                    {"id": "acknowledge", "label": "I'm OK"},
                ]
                if is_siren
                else [
                    {"id": "view-summary", "label": "View summary"},
                    {"id": "acknowledge", "label": "Got it"},
                ]
            ),
        },
        "trace": ["context", "listen", "dispatch", "architect", "executor"],
        "_fallback": {
            "mode": "local-demo",
            "reason": "Next pipeline unavailable; used backend-local fallback.",
        },
    }


async def run_existing_pipeline(
    *,
    transcript: str,
    confidence: float,
    scenario: ScenarioName,
) -> dict[str, Any]:
    body = {
        "listenInput": {
            "transcript": transcript,
            "source": "microphone",
            "confidenceHint": confidence,
        },
        "rawContext": build_raw_context(scenario),
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(settings.next_pipeline_url, json=body)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        if settings.demo_mode:
            return _build_local_demo_result(
                transcript=transcript,
                confidence=confidence,
                scenario=scenario,
            )
        raise

    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Unknown Next pipeline error."))

    return payload["result"]


def map_pipeline_to_events(
    result: dict[str, Any],
    scenario: ScenarioName,
) -> list[ServerEvent]:
    architect = result["architect"]
    dispatch = result["dispatch"]
    executor = result["executor"]
    observation = result["observation"]
    specialist = "vehicle" if architect["mode"] == "emergency" else "name"
    first_action = architect["recommendedActions"][0] if architect["recommendedActions"] else "Check details"

    return [
        {
            "type": "sound_detected",
            "text": observation["detectedSignal"].replace("_", " "),
            "latency_ms": round(float(observation["confidence"]) * 1000),
        },
        {
            "type": "agent_update",
            "agent": "dispatch",
            "status": "active",
            "output": f'DispatchAgent: classifying {dispatch["signal"]}',
        },
        {
            "type": "agent_update",
            "agent": "dispatch",
            "status": "done",
            "output": dispatch["reasoning"],
        },
        {
            "type": "agent_update",
            "agent": specialist,
            "status": "active",
            "output": f'{architect["mode"]} specialist: evaluating next action',
        },
        {
            "type": "agent_update",
            "agent": specialist,
            "status": "done",
            "output": f'{architect["title"]} - {first_action}',
        },
        {
            "type": "alert",
            "scenario": "name" if scenario == "hospital" else "siren",
            "title": executor["phoneTitle"],
            "subtitle": executor["phoneBody"],
            "risk": architect["severity"].upper(),
        },
    ]
