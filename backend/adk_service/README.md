# ADK Live Service

Python ai-service scaffold for the real-time audio path.

This service is intentionally separate from the current TypeScript rule pipeline.
The plan is:

1. Browser streams mic audio to this service over WebSocket.
2. Gemini Live handles real-time listening and transcription.
3. ADK-style specialist routing runs on the Python side.
4. During migration, the service can still bridge into the existing Next.js
   pipeline so the rest of the stack remains usable.
5. Frontend reconnection can happen later without changing the core backend flow.

Current scope:
- WebSocket message contract
- session state
- transcript runtime abstraction
- orchestration mode switch (`bridge` -> later `adk`)
- audio decode boundary for browser `audio/webm` chunks
- event mapping contract
- bridge into `POST /api/live/ingest`
- agent prompt pack for Dispatch / Vehicle / Name / Alert planning
- ADK agent graph scaffold

Not implemented yet:
- real Gemini Live audio transport
- live ADK runner wiring
- browser-webm -> pcm16 transcoding
- production buffering / reconnection / auth

Run:

```bash
cd backend/adk_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Environment:
- `NEXT_PIPELINE_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `ADK_AGENT_MODEL`
- `ADK_APP_NAME`
- `ADK_SERVICE_DEMO_MODE`
- `ADK_ORCHESTRATION_MODE=bridge|adk`
- `ADK_AUDIO_INPUT_MODE=browser-webm|pcm16`

Notes:
- the service derives `GOOGLE_API_KEY` from `GEMINI_API_KEY` for ADK calls
- `ADK_AGENT_MODEL` lets us lower cost / change backend reasoning models without touching the rest of the live stack
- `ADK_APP_NAME` stays configurable because ADK infers app names from local package layout during session lookup

ADK scaffold:

- `agents/myindigo/agent.py` defines the root agent and specialists
- `agents/myindigo/tools.py` exposes pipeline bridge tools
- `app/orchestrator.py` isolates the execution path so we can swap `bridge` for `adk` without touching the websocket layer
- the next step is wiring the runtime to invoke the ADK root agent when a final transcript arrives
- `GeminiLiveRuntime` now owns session lifecycle, but real audio only works once input is PCM16 or transcoded server-side

Audio chunk contract:

```json
{
  "type": "audio_chunk",
  "data": "<base64-bytes>",
  "format": "browser-webm | pcm16",
  "sample_rate_hz": 16000
}
```

Rules:
- `browser-webm` is for scaffold/demo mode
- `pcm16` + `16000Hz` is the real live path
- server-side transcoding is deferred on purpose to keep the first live implementation simple
