# myIndigo

Real-time audio awareness for deaf and hard-of-hearing users. Your phone listens, understands what it hears, and tells you what to do — on your phone and Apple Watch.

**NYC Build With AI Hackathon @ NYU Tandon — March 2026**

[Pitch Deck](https://www.figma.com/deck/ebsg6XMvEQVfHLcYQmva4Z/myIndigo_Google?node-id=1-133&viewport=-124%2C-31%2C0.59&t=TTdyLd0Ns68gQfd3-1&scaling=min-zoom&content-scaling=fixed&page-id=0%3A1) · [Demo Video](https://drive.google.com/file/d/1Ic5Nt25LI1L3mll7LpblyA9hC5c_LEzM/view?usp=sharing)

---

## The Problem

Existing tools either transcribe everything (Ava, Live Transcribe) or detect sound categories (iPhone Sound Recognition). Neither tells you *what to do*. "Siren detected" doesn't help when you're crossing the street and a fire truck is behind you.

## What myIndigo Does

Tap "Go live," pocket your phone, forget about it. When something critical happens, your wrist buzzes with a specific instruction.

- **Emergency sirens** → *"Move to the right. Fire truck approaching from behind."*
- **Subway announcements** → *"Your stop is next. Get ready to exit."*

Audio goes in, an action comes out. Gemini 2.5 Flash classifies the sound (siren? speech? ambient?), then specialized ADK agents reason about context and generate the alert. The whole pipeline runs over WebSocket in seconds.

## Key Decisions

**Single model for everything vs. dedicated audio classifier.**
We use Gemini Flash for classification, siren analysis, and speech summarization. A lightweight classifier (like YAMNet) as a first pass would be smarter at scale — less latency, lower cost — but the single-model approach cut integration complexity in half during a 36-hour build and was accurate enough for demo.

**Deterministic routing over LLM routing.**
After classification, a simple if/else orchestrator routes to the right agent. We could have let the LLM decide routing too, but misrouting a siren to the speech summarizer is a safety failure, not a UX annoyance. Hard rules felt right for that.

## What I Learned

- Siren detection hit ~85% accuracy in a quiet room but dropped to ~60% with street noise. A production version needs noise-gating before the audio reaches the model.
- The real UX problem was alert fatigue, not detection. The system triggered on ambulances five blocks away. Confidence thresholds help; spatial/GPS context would actually solve it.

## How it works

```
Microphone (browser)
    |  PCM16 audio @ 16kHz
    v
WebSocket --> Python FastAPI backend
    |
    v
+----------------------------------+
|  Gemini 2.5 Flash (multimodal)   |
|  Audio classification +          |
|  transcription                   |
|  "Is this a siren or speech?"    |
+----------+-----------------------+
           |
     +-----+-----+
     |           |
   SIREN      SPEECH
     |           |
     v           v
+----------+ +---------------+
| SirenAgent | SummaryAgent  |
| (ADK)    | | (ADK)         |
| Confirms | | Categorizes   |
| + action | | + action      |
+----+-----+ +------+--------+
     |              |
     v              v
  WebSocket --> Phone + Watch alert
```

**Audio in, action out.** Gemini processes raw audio (multimodal), ADK agents reason about it, and the user gets a clear instruction on their device in seconds.

## Tech stack

| Layer            | Technology                             |
| ---------------- | -------------------------------------- |
| Frontend         | Next.js 14 + TypeScript                |
| Backend          | Python 3.11 + FastAPI                  |
| AI Orchestration | Google ADK (Agent Development Kit)     |
| AI Model         | Gemini 2.5 Flash (Google GenAI SDK)    |
| Real-time        | WebSocket (browser <-> Python backend) |
| Audio Capture    | Web Audio API, PCM16 @ 16kHz           |
| Database         | PostgreSQL on Supabase                 |
| Auth             | Supabase Auth                          |


## Setup

Requires Node.js 18+, Python 3.11+, [Google AI Studio API key](https://aistudio.google.com/apikey), Supabase project.

```bash
git clone https://github.com/yunLeia/indigo-ai-agent.git
cd indigo-ai-agent && npm install
cp .env.example .env.local  # fill in your keys

cd backend/adk_service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create backend/adk_service/.env with GEMINI_API_KEY, etc.

# Terminal 1: uvicorn app.main:app --port 8001 --reload
# Terminal 2: npm run dev
```

Open `localhost:3000`, click **Go live**, allow mic. Play a siren or speak a subway announcement to test.
