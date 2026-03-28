from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config import settings

log = logging.getLogger("myindigo.adk")

_SESSION_SERVICE = InMemorySessionService()


def _coerce_json(raw_text: str) -> Dict[str, Any]:
    """Extract a JSON object from agent output, handling markdown wrapping."""
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
    return "\n".join(f for f in fragments if f).strip()


async def run_agent(
    *,
    agent_name: str,
    transcript: str,
    user_name: str,
) -> Dict[str, Any]:
    """
    Run a specialist ADK agent (siren_agent or name_agent) and return parsed JSON.
    """
    # Set API key for ADK
    if settings.adk_gemini_api_key:
        os.environ["GOOGLE_API_KEY"] = settings.adk_gemini_api_key
        os.environ.pop("GEMINI_API_KEY", None)

    # Load the right agent
    if agent_name == "siren":
        from agents.myindigo.agent import siren_agent as agent
        prompt = (
            f"Audio monitor detected an emergency sound.\n"
            f"Transcript/description from audio: \"{transcript}\"\n"
            f"User context: deaf/hard-of-hearing pedestrian in NYC.\n"
            f"Analyze and respond with JSON."
        )
    elif agent_name == "name":
        from agents.myindigo.agent import name_agent as agent
        prompt = (
            f"Audio monitor detected speech from a microphone.\n"
            f"Transcript: \"{transcript}\"\n"
            f"Determine if this is a subway, transit, or public announcement and respond with JSON."
        )
    elif agent_name == "summary":
        from agents.myindigo.agent import summary_agent as agent
        prompt = (
            f"Audio monitor detected speech.\n"
            f"Transcript: \"{transcript}\"\n"
            f"User context: deaf/hard-of-hearing user in NYC.\n"
            f"Summarize this speech, categorize it, pick an icon, and explain what action to take. Respond with JSON."
        )
    else:
        raise ValueError(f"Unknown agent: {agent_name}")

    log.info(
        "[ADK] >> Calling %s | prompt=%r",
        agent.name,
        prompt[:120],
    )
    start = time.time()

    # Run the agent
    async with Runner(
        app_name=settings.adk_app_name,
        agent=agent,
        session_service=_SESSION_SERVICE,
    ) as runner:
        session = await _SESSION_SERVICE.create_session(
            app_name=settings.adk_app_name,
            user_id=user_name,
            session_id=str(uuid4()),
        )

        final_text = ""
        async for event in runner.run_async(
            user_id=user_name,
            session_id=session.id,
            new_message=types.UserContent(parts=[types.Part(text=prompt)]),
        ):
            if event.author == agent.name and event.is_final_response():
                candidate = _content_to_text(event.content)
                if candidate:
                    final_text = candidate

    elapsed_ms = int((time.time() - start) * 1000)

    if not final_text:
        log.warning("[ADK] %s returned empty response after %dms", agent.name, elapsed_ms)
        raise RuntimeError(f"{agent.name} returned no response")

    log.info(
        "[ADK] << %s responded in %dms | raw=%r",
        agent.name,
        elapsed_ms,
        final_text[:200],
    )

    result = _coerce_json(final_text)
    log.info(
        "[ADK] << %s parsed JSON | confirmed=%s | title=%r",
        agent.name,
        result.get("confirmed"),
        result.get("title"),
    )
    return result
