"use client";

import { useRef, useState, useCallback, useEffect } from "react";

// Messages FROM backend
export type ServerMessage =
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

// Messages TO backend
type ClientMessage =
  | { type: "init"; user_name: string; user_id: string }
  | { type: "audio_chunk"; data: string };

type UseAgentWebSocketOptions = {
  url: string;
  userName: string;
  userId: string;
  onMessage: (msg: ServerMessage) => void;
  onConnectionChange?: (connected: boolean) => void;
};

export function useAgentWebSocket({
  url,
  userName,
  userId,
  onMessage,
  onConnectionChange,
}: UseAgentWebSocketOptions) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const onConnectionChangeRef = useRef(onConnectionChange);

  // Keep refs fresh without triggering reconnect
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    onConnectionChangeRef.current = onConnectionChange;
  }, [onConnectionChange]);

  const connect = useCallback(() => {
    if (wsRef.current) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      onConnectionChangeRef.current?.(true);

      // Send init message with user context
      const init: ClientMessage = {
        type: "init",
        user_name: userName,
        user_id: userId,
      };
      ws.send(JSON.stringify(init));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as ServerMessage;
        onMessageRef.current(msg);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnected(false);
      onConnectionChangeRef.current?.(false);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url, userName, userId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendAudioChunk = useCallback((base64: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const msg: ClientMessage = { type: "audio_chunk", data: base64 };
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { connected, connect, disconnect, sendAudioChunk };
}
