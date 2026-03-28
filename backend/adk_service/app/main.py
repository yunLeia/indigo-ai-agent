from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.config import settings
from app.contracts import AudioChunkMessage, DebugOrchestrateRequest, InitMessage
from app.orchestrator import run_orchestration
from app.runtime import build_runtime
from app.session import AudioSession

app = FastAPI(title="myIndigo ADK Live Service")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "service": "adk-live-service"}


@app.get("/debug/config")
async def debug_config() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "adk-live-service",
        "demo_mode": settings.demo_mode,
        "orchestration_mode": settings.orchestration_mode,
        "audio_input_mode": settings.audio_input_mode,
        "model": settings.gemini_model,
        "adk_agent_model": settings.adk_agent_model,
        "adk_app_name": settings.adk_app_name,
    }


@app.post("/debug/orchestrate")
async def debug_orchestrate(body: DebugOrchestrateRequest) -> dict[str, Any]:
    result, events = await run_orchestration(
        transcript=body.transcript,
        confidence=body.confidence,
        scenario=body.scenario,
        user_name=body.user_name,
        mode_override=body.mode,
    )
    return {
        "ok": True,
        "mode": body.mode or settings.orchestration_mode,
        "result": result,
        "events": events,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    runtime = build_runtime()
    session: Optional[AudioSession] = None

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type")

            if message_type == "init":
                init = InitMessage.model_validate(payload)
                session = AudioSession(
                    user_name=init.user_name,
                    user_id=init.user_id,
                    scenario=init.scenario or "siren",
                )
                continue

            if message_type != "audio_chunk" or session is None:
                continue

            chunk = AudioChunkMessage.model_validate(payload)
            frame = await runtime.ingest_audio(session, chunk)

            if frame is None or not frame.is_final:
                continue

            _, events = await run_orchestration(
                transcript=frame.text,
                confidence=frame.confidence,
                scenario=frame.scenario,
                user_name=session.user_name,
            )

            for index, event in enumerate(events):
                if index:
                    await asyncio.sleep(0.45)
                await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        if session is not None:
            await runtime.close_session(session)
        await runtime.shutdown()
