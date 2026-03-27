import { serverEnv } from "@/lib/env/server";
import type { LiveSessionConfig } from "@/types/live-agent";

const LIVE_SYSTEM_INSTRUCTION = [
  "You are myIndigo, an accessibility-focused live safety agent.",
  "Listen for environmental signals, classify them, reason with context, and prepare concise alerts.",
  "Prioritize emergency hazards such as sirens, fire alarms, and crashes.",
  "Summarize public announcements clearly when they are informative but not safety critical.",
  "Keep messages wearable-friendly, short, and action-oriented.",
].join(" ");

export function buildLiveSessionConfig(): LiveSessionConfig {
  return {
    provider: "gemini-live",
    configured: Boolean(serverEnv.geminiApiKey),
    model: serverEnv.geminiModel,
    responseModalities: ["TEXT"],
    inputAudioTranscription: true,
    systemInstruction: LIVE_SYSTEM_INSTRUCTION,
    supportedScenarios: [
      "emergency_vehicle",
      "hospital_pa",
      "airport_pa",
      "home",
    ],
    transport: "websocket",
    pipelineStages: ["context", "listen", "dispatch", "architect", "executor"],
  };
}
