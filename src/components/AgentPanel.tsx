"use client";

export type AgentStepStatus = "inactive" | "active" | "done";

export type AgentStep = {
  id: string;
  label: string;
  sub: string;
  icon: string;
  status: AgentStepStatus;
};

type AgentPanelProps = {
  steps: AgentStep[];
  elapsed: number;
};

export default function AgentPanel({ steps, elapsed }: AgentPanelProps) {
  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>Agent reasoning chain</div>
      {steps.map((step, i) => {
        const cls =
          step.status === "active"
            ? "active"
            : step.status === "done"
              ? "done"
              : "inactive";
        return (
          <div
            key={`${step.id}-${i}`}
            style={{
              ...styles.step,
              opacity: cls === "inactive" ? 0.25 : cls === "done" ? 0.7 : 1,
            }}
          >
            <div
              style={{
                ...styles.stepIcon,
                ...(cls === "active"
                  ? {
                      background: "#16142a",
                      borderColor: "#7F77DD",
                      color: "#CECBF6",
                    }
                  : cls === "done"
                    ? {
                        background: "#0a1710",
                        borderColor: "#1D9E75",
                        color: "#9FE1CB",
                      }
                    : {}),
              }}
            >
              {cls === "done" ? (
                "✓"
              ) : cls === "active" ? (
                <>
                  {step.icon}
                  <span style={styles.spin} />
                </>
              ) : (
                step.icon
              )}
            </div>
            <div>
              <div
                style={{
                  ...styles.stepLabel,
                  color:
                    cls === "active"
                      ? "#fff"
                      : cls === "done"
                        ? "#9FE1CB"
                        : "#444",
                }}
              >
                {step.label}
              </div>
              {step.sub && (
                <div
                  style={{
                    ...styles.stepSub,
                    color: cls === "active" || cls === "done" ? "#666" : "#333",
                  }}
                >
                  {step.sub}
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div style={styles.timerBar}>
        <div style={styles.timerLabel}>Time: sound → alert</div>
        <div style={styles.timerVal}>
          {elapsed > 0 ? `${(elapsed / 1000).toFixed(1)}s` : "—"}
        </div>
      </div>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    background: "#141414",
    border: "0.5px solid #222",
    borderRadius: 10,
    padding: 14,
  },
  panelTitle: {
    fontSize: 10,
    color: "#444",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 12,
  },
  step: {
    display: "flex",
    gap: 8,
    alignItems: "flex-start",
    marginBottom: 10,
    transition: "all 0.4s",
  },
  stepIcon: {
    width: 22,
    height: 22,
    borderRadius: 6,
    background: "#1a1a1a",
    border: "1px solid #2a2a2a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 9,
    fontWeight: 700,
    color: "#555",
    flexShrink: 0,
    transition: "all 0.3s",
  },
  stepLabel: {
    fontSize: 11,
    fontWeight: 500,
    color: "#444",
    transition: "color 0.3s",
    lineHeight: 1.3,
  },
  stepSub: {
    fontSize: 10,
    color: "#333",
    marginTop: 2,
    lineHeight: 1.4,
    transition: "color 0.3s",
  },
  spin: {
    width: 8,
    height: 8,
    border: "1.5px solid #333",
    borderTopColor: "#7F77DD",
    borderRadius: "50%",
    display: "inline-block",
    animation: "spin 0.6s linear infinite",
    marginLeft: 4,
    verticalAlign: "middle",
  },
  timerBar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: 4,
  },
  timerLabel: {
    fontSize: 10,
    color: "#444",
  },
  timerVal: {
    fontSize: 11,
    fontWeight: 500,
    color: "#9FE1CB",
    fontVariantNumeric: "tabular-nums",
  },
};
