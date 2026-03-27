"use client";

import type { AlertEvent } from "./DemoScreen";

type PhoneMockupProps = {
  alert: AlertEvent | null;
  scenario: "siren" | "hospital";
  radarActive: boolean;
  locationText: string;
};

export default function PhoneMockup({
  alert,
  scenario,
  radarActive,
  locationText,
}: PhoneMockupProps) {
  const isSiren = alert?.scenario === "siren";

  return (
    <div style={styles.frame}>
      <div style={styles.notch} />
      <div style={styles.screen}>
        <div style={styles.mapBg}>
          <div style={styles.locationWrap}>
            <span style={styles.locationText}>{locationText}</span>
          </div>
          <div style={styles.radar}>
            <div style={styles.radarMid} />
            <div style={styles.radarInner} />
            <div style={styles.radarDot} />
            {radarActive && scenario === "siren" && (
              <div style={styles.sirenDot} />
            )}
          </div>
        </div>
        {alert && (
          <div
            style={{
              ...styles.phoneAlert,
              background: isSiren
                ? "rgba(226,75,74,0.12)"
                : "rgba(127,119,221,0.12)",
              borderTop: isSiren
                ? "0.5px solid rgba(226,75,74,0.3)"
                : "0.5px solid rgba(127,119,221,0.3)",
            }}
          >
            <div
              style={{
                ...styles.phoneAlertTitle,
                color: isSiren ? "#ff6b6b" : "#CECBF6",
              }}
            >
              {alert.title}
            </div>
            <div style={styles.phoneAlertSub}>{alert.subtitle}</div>
          </div>
        )}
        <div style={styles.phoneBottom}>
          <div style={styles.phoneBtn}>Agent</div>
          <div style={styles.phoneBtn}>Settings</div>
        </div>
      </div>
      <style>{`
        @keyframes sirenPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  frame: {
    background: "#111",
    border: "3px solid #2a2a2a",
    borderRadius: 48,
    padding: 14,
    width: 300,
    flexShrink: 0,
  },
  notch: {
    width: 80,
    height: 8,
    background: "#1a1a1a",
    borderRadius: 4,
    margin: "0 auto 10px",
  },
  screen: {
    background: "#1a1a2e",
    borderRadius: 34,
    overflow: "hidden",
    height: 520,
    position: "relative",
    display: "flex",
    flexDirection: "column",
  },
  mapBg: {
    flex: 1,
    background: "linear-gradient(180deg, #1a1f3a 0%, #111827 100%)",
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  locationWrap: {
    position: "absolute",
    top: 14,
    left: 0,
    right: 0,
    textAlign: "center",
  },
  locationText: {
    fontSize: 12,
    color: "#6366f1",
    background: "rgba(99,102,241,0.1)",
    borderRadius: 12,
    padding: "3px 12px",
    display: "inline-block",
  },
  radar: {
    width: 150,
    height: 150,
    borderRadius: "50%",
    border: "1px solid rgba(99,102,241,0.2)",
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  radarMid: {
    position: "absolute",
    inset: 24,
    borderRadius: "50%",
    border: "1px solid rgba(99,102,241,0.15)",
  },
  radarInner: {
    position: "absolute",
    inset: 48,
    borderRadius: "50%",
    border: "1px solid rgba(99,102,241,0.1)",
  },
  radarDot: {
    width: 10,
    height: 10,
    borderRadius: "50%",
    background: "#6366f1",
  },
  sirenDot: {
    position: "absolute",
    width: 14,
    height: 14,
    borderRadius: "50%",
    background: "#E24B4A",
    top: 14,
    right: 24,
    animation: "sirenPulse 1s infinite",
  },
  phoneAlert: {
    padding: "14px 16px",
  },
  phoneAlertTitle: {
    fontSize: 14,
    fontWeight: 600,
  },
  phoneAlertSub: {
    fontSize: 11,
    color: "#888",
    marginTop: 3,
  },
  phoneBottom: {
    background: "#111",
    borderRadius: "0 0 34px 34px",
    padding: 12,
    display: "flex",
    justifyContent: "center",
    gap: 20,
  },
  phoneBtn: {
    background: "#1a1a1a",
    borderWidth: "0.5px",
    borderStyle: "solid",
    borderColor: "#2a2a2a",
    borderRadius: 10,
    padding: "7px 16px",
    fontSize: 11,
    color: "#888",
  },
};
