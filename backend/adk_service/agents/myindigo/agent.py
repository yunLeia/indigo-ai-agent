from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from app.config import settings
from app.prompts import (
    ALERT_PLANNER_PROMPT,
    DISPATCH_AGENT_PROMPT,
    NAME_DETECTION_AGENT_PROMPT,
    VEHICLE_SOUND_AGENT_PROMPT,
)
from agents.myindigo.tools import (
    assess_vehicle_sound,
    build_alert_payload,
    extract_name_announcement,
)

MODEL_NAME = settings.adk_agent_model

vehicle_sound_agent = Agent(
    model=MODEL_NAME,
    name="vehicle_sound_agent",
    description="Analyzes emergency vehicle sounds and returns actionable risk guidance.",
    instruction=VEHICLE_SOUND_AGENT_PROMPT,
    tools=[assess_vehicle_sound],
)

name_detection_agent = Agent(
    model=MODEL_NAME,
    name="name_detection_agent",
    description="Extracts user-relevant public announcement details.",
    instruction=NAME_DETECTION_AGENT_PROMPT,
    tools=[extract_name_announcement],
)

alert_planner_agent = Agent(
    model=MODEL_NAME,
    name="alert_planner_agent",
    description="Formats specialist outputs into phone and wearable alert payloads.",
    instruction=ALERT_PLANNER_PROMPT,
    tools=[build_alert_payload],
)

root_agent = Agent(
    model=MODEL_NAME,
    name="dispatch_agent",
    description="Always-on routing agent for myIndigo realtime audio scenarios.",
    instruction=DISPATCH_AGENT_PROMPT,
    sub_agents=[
        vehicle_sound_agent,
        name_detection_agent,
        alert_planner_agent,
    ],
)
