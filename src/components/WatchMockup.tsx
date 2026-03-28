"use client";

import type { AlertEvent } from "./DemoScreen";

type WatchMockupProps = {
  alert: AlertEvent | null;
};

export default function WatchMockup({ alert }: WatchMockupProps) {
  const isSiren = alert?.scenario === "siren";
  const isSpeech = alert?.scenario === "speech";

  return (
    <div style={styles.frame}>
      <div style={styles.watchTime}>9:41</div>
      <div
        style={{
          ...styles.screen,
          ...(alert
            ? isSiren
              ? {
                  background: "#1a0808",
                  borderColor: "rgba(226,75,74,0.3)",
                }
              : isSpeech
                ? {
                    background: "#081a2a",
                    borderColor: "rgba(100,200,255,0.3)",
                  }
                : {
                    background: "#110f1f",
                    borderColor: "rgba(127,119,221,0.3)",
                  }
            : {}),
        }}
      >
        {alert ? (
          <div style={styles.alertWrap}>
            <div
              style={{
                ...styles.watchIcon,
                background: isSiren
                  ? "#E24B4A"
                  : isSpeech
                    ? "#64c8ff"
                    : "#7F77DD",
              }}
            >
              {alert.icon ? alert.icon[0] : isSiren ? "!" : "+"}
            </div>
            <div style={styles.watchTitle}>{alert.title}</div>
            <div style={styles.watchSub}>{alert.subtitle.substring(0, 50)}</div>
            {alert.action && (
              <div style={styles.watchAction}>
                ➜ {alert.action.substring(0, 30)}
              </div>
            )}
          </div>
        ) : (
          <div style={styles.watchEmpty}>Waiting...</div>
        )}
      </div>
      <style>{`
        @keyframes wPop {
          from { transform: scale(0.5); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  frame: {
    width: 210,
    background: "#111",
    border: "3px solid #2a2a2a",
    borderRadius: 38,
    padding: 12,
    flexShrink: 0,
  },
  watchTime: {
    fontSize: 14,
    color: "#555",
    textAlign: "center",
    paddingTop: 6,
    paddingBottom: 6,
  },
  screen: {
    background: "#0a0a0a",
    borderRadius: 28,
    height: 240,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: 18,
    textAlign: "center",
    transition: "all 0.5s",
    borderWidth: 1,
    borderStyle: "solid",
    borderColor: "transparent",
  },
  watchEmpty: {
    fontSize: 13,
    color: "#333",
  },
  alertWrap: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    animation: "wPop 0.3s ease-out",
  },
  watchIcon: {
    width: 44,
    height: 44,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 20,
    fontWeight: 700,
    color: "#fff",
    marginBottom: 12,
  },
  watchTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: "#fff",
    lineHeight: 1.3,
    marginBottom: 6,
  },
  watchSub: {
    fontSize: 11,
    color: "#777",
    lineHeight: 1.3,
  },
  watchAction: {
    fontSize: 9,
    color: "#666",
    marginTop: 4,
    paddingTop: 4,
    borderTop: "0.5px solid rgba(255,255,255,0.1)",
    width: "100%",
  },
};
