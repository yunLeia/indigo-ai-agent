from __future__ import annotations

from google.adk.agents import LlmAgent

from app.config import settings
from app.prompts import SIREN_AGENT_PROMPT, NAME_AGENT_PROMPT

MODEL = settings.adk_agent_model

siren_agent = LlmAgent(
    name="siren_agent",
    model=MODEL,
    description="Confirms emergency vehicle sounds and assesses risk for deaf users.",
    instruction=SIREN_AGENT_PROMPT,
)

name_agent = LlmAgent(
    name="name_agent",
    model=MODEL,
    description="Confirms if a deaf user's name was called in a PA announcement.",
    instruction=NAME_AGENT_PROMPT,
)
