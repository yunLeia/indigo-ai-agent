"use client";

import { useMemo, useRef, useState } from "react";
import { usePcmAudioCapture, type PcmAudioChunk } from "@/hooks/usePcmAudioCapture";

type ServerEvent =
  | { type: "sound_detected"; text: string; latency_ms: number }
  | {
      type: "agent_update";
      agent: string;
      status: "active" | "done";
      output: string;
    }
  | {
      type: "alert";
      scenario: "siren" | "name";
      title: string;
      subtitle: string;
      risk: string;
    };

const WS_URL = "ws://localhost:8001/ws";

export default function LiveAudioTestPage() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<ServerEvent[]>([]);
  const [scenario, setScenario] = useState<"siren" | "hospital">("siren");
  const [error, setError] = useState<string | null>(null);

  const { capturing, start, stop } = usePcmAudioCapture({
    onChunk: (chunk) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
        return;
      }

      wsRef.current.send(
        JSON.stringify({
          type: "audio_chunk",
          data: chunk.data,
          format: chunk.format,
          sample_rate_hz: chunk.sample_rate_hz,
        } satisfies PcmAudioChunk & { type: "audio_chunk" }),
      );
    },
  });

  const statusLabel = useMemo(() => {
    if (capturing) return "Capturing PCM16";
    if (connected) return "Connected";
    return "Disconnected";
  }, [capturing, connected]);

  function connect() {
    if (wsRef.current) {
      return;
    }

    const socket = new WebSocket(WS_URL);
    wsRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      setError(null);
      socket.send(
        JSON.stringify({
          type: "init",
          user_name: "Alex Kim",
          user_id: "pcm-live-test",
          scenario,
        }),
      );
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ServerEvent;
        setEvents((prev) => [payload, ...prev].slice(0, 24));
      } catch {
        setError("Received malformed event payload.");
      }
    };

    socket.onclose = () => {
      wsRef.current = null;
      setConnected(false);
    };

    socket.onerror = () => {
      setError("WebSocket connection failed.");
    };
  }

  function disconnect() {
    stop();
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }

  async function startLive() {
    try {
      connect();
      await start();
    } catch (captureError) {
      setError(
        captureError instanceof Error
          ? captureError.message
          : "Failed to start PCM audio capture.",
      );
    }
  }

  return (
    <main
      style={{
        maxWidth: 920,
        margin: "0 auto",
        padding: "48px 24px 80px",
        display: "grid",
        gap: 20,
      }}
    >
      <header style={{ display: "grid", gap: 10 }}>
        <span
          style={{
            width: "fit-content",
            borderRadius: 999,
            padding: "6px 12px",
            background: "#e5eefc",
            color: "#2447a6",
            fontSize: 12,
            fontWeight: 700,
          }}
        >
          Step 16
        </span>
        <h1 style={{ margin: 0 }}>PCM16 live audio contract test</h1>
        <p style={{ margin: 0, color: "#516074", lineHeight: 1.7 }}>
          This page does not replace the teammate demo. It only verifies that
          the new PCM capture path can talk to the Python ai-service over
          WebSocket using the live contract we defined.
        </p>
      </header>

      <section
        style={{
          border: "1px solid #d7deea",
          borderRadius: 20,
          background: "#fff",
          padding: 20,
          display: "grid",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            onClick={() => setScenario("siren")}
            style={{
              padding: "10px 16px",
              borderRadius: 999,
              border: "1px solid #cfd7e4",
              background: scenario === "siren" ? "#162742" : "#fff",
              color: scenario === "siren" ? "#fff" : "#223249",
              cursor: "pointer",
            }}
            type="button"
          >
            Emergency vehicle
          </button>
          <button
            onClick={() => setScenario("hospital")}
            style={{
              padding: "10px 16px",
              borderRadius: 999,
              border: "1px solid #cfd7e4",
              background: scenario === "hospital" ? "#162742" : "#fff",
              color: scenario === "hospital" ? "#fff" : "#223249",
              cursor: "pointer",
            }}
            type="button"
          >
            Hospital PA
          </button>
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            onClick={startLive}
            style={{
              padding: "12px 18px",
              borderRadius: 14,
              border: "none",
              background: "#1f4ed8",
              color: "#fff",
              cursor: "pointer",
            }}
            type="button"
          >
            Start PCM live test
          </button>
          <button
            onClick={disconnect}
            style={{
              padding: "12px 18px",
              borderRadius: 14,
              border: "1px solid #cfd7e4",
              background: "#fff",
              color: "#223249",
              cursor: "pointer",
            }}
            type="button"
          >
            Stop
          </button>
          <div
            style={{
              alignSelf: "center",
              fontSize: 14,
              color: "#516074",
            }}
          >
            Status: {statusLabel}
          </div>
        </div>

        {error ? (
          <div
            style={{
              borderRadius: 14,
              background: "#fff2f2",
              color: "#a12d2d",
              border: "1px solid #efc6c6",
              padding: "12px 14px",
            }}
          >
            {error}
          </div>
        ) : null}
      </section>

      <section
        style={{
          border: "1px solid #d7deea",
          borderRadius: 20,
          background: "#fff",
          padding: 20,
          display: "grid",
          gap: 12,
        }}
      >
        <h2 style={{ margin: 0 }}>Incoming events</h2>
        <pre
          style={{
            margin: 0,
            padding: 16,
            borderRadius: 16,
            background: "#0f172a",
            color: "#dbe6ff",
            overflowX: "auto",
            lineHeight: 1.5,
            fontSize: 13,
          }}
        >
          {JSON.stringify(events, null, 2)}
        </pre>
      </section>
    </main>
  );
}
