export type SignalLabel =
  | "fire_alarm"
  | "emergency_vehicle_siren"
  | "hospital_pa"
  | "airport_pa"
  | "name_called"
  | "doorbell"
  | "conversation"
  | "ambient_noise";

export type SignalCategory = "emergency" | "info" | "routine" | "unknown";

export type AudioSource = "simulation" | "microphone" | "upload";

export type AudioObservation = {
  transcript: string;
  detectedSignal: SignalLabel;
  confidence: number;
  timestampIso: string;
  source: AudioSource;
};

export type DispatchDecision = {
  category: SignalCategory;
  signal: SignalLabel;
  confidence: number;
  routeTo: "architect";
  reasoning: string;
};

export type ArchitectSeverity = "low" | "medium" | "high" | "critical";

export type WearableSignal =
  | "strong-vibration"
  | "standard-vibration"
  | "visual-only";

export type EscalationMode = "notify-now" | "surface-now" | "log-only";

export type ContextSnapshot = {
  locationLabel?: string;
  environmentLabel?: string;
};

export type ArchitectDecision = {
  severity: ArchitectSeverity;
  title: string;
  userMessage: string;
  recommendedActions: string[];
  wearableSignal: WearableSignal;
  escalation: EscalationMode;
};
