from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import settings
from app.contracts import ScenarioName


_SESSION_SERVICE = InMemorySessionService()


def _load_agents():
    from agents.myindigo.agent import (
        alert_planner_agent,
        name_detection_agent,
        vehicle_sound_agent,
    )

    return vehicle_sound_agent, name_detection_agent, alert_planner_agent


def _coerce_json_object(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _content_to_text(content: Optional[types.Content]) -> str:
    if not content or not content.parts:
        return ""

    fragments: List[str] = []
    for part in content.parts:
        if getattr(part, "text", None):
            fragments.append(part.text)
    return "\n".join(fragment for fragment in fragments if fragment).strip()


async def _run_agent_once(
    *,
    agent,
    user_id: str,
    prompt: str,
    state: Optional[Dict[str, Any]] = None,
) -> str:
    runner = Runner(
        app_name=settings.adk_app_name,
        agent=agent,
        session_service=_SESSION_SERVICE,
    )
    session = await _SESSION_SERVICE.create_session(
        app_name=settings.adk_app_name,
        user_id=user_id,
        session_id=str(uuid4()),
        state=state or {},
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.UserContent(parts=[types.Part(text=prompt)]),
    ):
        if event.author == agent.name and event.is_final_response():
            candidate = _content_to_text(event.content)
            if candidate:
                final_text = candidate

    if not final_text:
        raise RuntimeError(f"{agent.name} did not return a final text response.")

    return final_text


def _build_specialist_prompt(
    *,
    transcript: str,
    scenario: ScenarioName,
    user_name: str,
) -> str:
    if scenario == "siren":
        return f"""
Transcript: {transcript}
Scenario: emergency vehicle outdoors
User name: {user_name}
User state: on foot
Likely location: Chelsea, NYC
Direction hint: behind

Analyze this as a real-time sound safety event and return the JSON format exactly.
""".strip()

    return f"""
Transcript: {transcript}
Scenario: hospital public announcement
User name: {user_name}
Location type: hospital waiting room
Likely location: NYU Langone lobby

Analyze whether the user was called and return the JSON format exactly.
""".strip()


def _build_planner_prompt(
    *,
    transcript: str,
    scenario: ScenarioName,
    user_name: str,
    specialist_result: Dict[str, Any],
) -> str:
    return f"""
User name: {user_name}
Scenario: {scenario}
Transcript: {transcript}
Specialist result JSON:
{json.dumps(specialist_result, ensure_ascii=True)}

Convert this into the strict architect/executor JSON format exactly.
""".strip()


def _build_fallback_result(
    *,
    transcript: str,
    scenario: ScenarioName,
    specialist_result: Dict[str, Any],
    planner_result: Dict[str, Any],
) -> Dict[str, Any]:
    is_emergency = scenario == "siren"
    signal = specialist_result.get(
        "signal",
        "emergency_vehicle_siren" if is_emergency else "hospital_pa",
    )
    title = specialist_result.get(
        "title",
        "Emergency vehicle approaching" if is_emergency else "Your name was called",
    )
    subtitle = specialist_result.get(
        "subtitle",
        "Move right and yield" if is_emergency else "Go to Exam Room 3",
    )
    recommended_actions = specialist_result.get(
        "recommended_actions",
        ["Move right", "Check surroundings"]
        if is_emergency
        else ["Read summary", "Go to destination"],
    )

    architect = planner_result.get("architect") or {
        "mode": "emergency" if is_emergency else "info",
        "severity": "high" if is_emergency else "medium",
        "title": title,
        "userMessage": subtitle,
        "recommendedActions": recommended_actions,
        "wearableSignal": "strong-vibration" if is_emergency else "standard-vibration",
        "escalation": "notify-now" if is_emergency else "surface-now",
    }
    executor = planner_result.get("executor") or {
        "channel": "phone-and-wearable",
        "phoneTitle": title,
        "phoneBody": subtitle,
        "wearableTitle": title,
        "wearableBody": subtitle,
        "vibration": "strong" if is_emergency else "standard",
        "actions": (
            [{"id": "open-map", "label": "Show map"}, {"id": "acknowledge", "label": "I'm OK"}]
            if is_emergency
            else [{"id": "view-summary", "label": "View summary"}, {"id": "acknowledge", "label": "Got it"}]
        ),
    }

    return {
        "rawContext": {
            "scenarioHint": "emergency_vehicle" if is_emergency else "hospital_pa",
        },
        "context": {
            "scenarioLabel": "Emergency vehicle outdoors"
            if is_emergency
            else "Hospital public announcement",
            "locationLabel": "Chelsea, NYC" if is_emergency else "NYU Langone lobby",
            "environmentLabel": "street" if is_emergency else "hospital",
            "userSituation": "on_foot" if is_emergency else "waiting_room",
        },
        "observation": {
            "transcript": transcript,
            "detectedSignal": signal,
            "confidence": 0.92 if is_emergency else 0.9,
            "timestampIso": datetime.now(timezone.utc).isoformat(),
            "source": "microphone",
        },
        "dispatch": {
            "category": "emergency" if is_emergency else "info",
            "signal": signal,
            "confidence": 0.92 if is_emergency else 0.9,
            "routeTo": "architect",
            "reasoning": specialist_result.get(
                "subtitle",
                "Specialist agent analyzed the live transcript.",
            ),
        },
        "architect": architect,
        "executor": executor,
        "trace": ["listen", "dispatch", "architect", "executor"],
    }


async def run_adk_reasoning(
    *,
    transcript: str,
    scenario: ScenarioName,
    user_name: str,
) -> Dict[str, Any]:
    if settings.gemini_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
        os.environ.pop("GEMINI_API_KEY", None)

    vehicle_sound_agent, name_detection_agent, alert_planner_agent = _load_agents()

    specialist_agent = vehicle_sound_agent if scenario == "siren" else name_detection_agent
    specialist_prompt = _build_specialist_prompt(
        transcript=transcript,
        scenario=scenario,
        user_name=user_name,
    )
    specialist_text = await _run_agent_once(
        agent=specialist_agent,
        user_id=user_name,
        prompt=specialist_prompt,
        state={"scenario": scenario},
    )
    specialist_result = _coerce_json_object(specialist_text)

    planner_prompt = _build_planner_prompt(
        transcript=transcript,
        scenario=scenario,
        user_name=user_name,
        specialist_result=specialist_result,
    )
    planner_text = await _run_agent_once(
        agent=alert_planner_agent,
        user_id=user_name,
        prompt=planner_prompt,
        state={"scenario": scenario},
    )
    planner_result = _coerce_json_object(planner_text)

    return _build_fallback_result(
        transcript=transcript,
        scenario=scenario,
        specialist_result=specialist_result,
        planner_result=planner_result,
    )
