"use client";

import { useRef, useState, useCallback } from "react";

type UseAudioCaptureOptions = {
  onChunk: (base64: string) => void;
  chunkIntervalMs?: number;
};

export function useAudioCapture({
  onChunk,
  chunkIntervalMs = 500,
}: UseAudioCaptureOptions) {
  const [capturing, setCapturing] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const start = useCallback(async () => {
    if (capturing) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const recorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm",
    });
    recorderRef.current = recorder;

    recorder.ondataavailable = async (e) => {
      if (e.data.size > 0) {
        const buffer = await e.data.arrayBuffer();
        const bytes = new Uint8Array(buffer);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64 = btoa(binary);
        onChunk(base64);
      }
    };

    recorder.start();

    // Periodically request data from the recorder
    intervalRef.current = setInterval(() => {
      if (recorder.state === "recording") {
        recorder.requestData();
      }
    }, chunkIntervalMs);

    setCapturing(true);
  }, [capturing, onChunk, chunkIntervalMs]);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      recorderRef.current.stop();
      recorderRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCapturing(false);
  }, []);

  return { capturing, start, stop };
}
