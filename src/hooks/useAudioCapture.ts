"use client";

import { usePcmAudioCapture } from "@/hooks/usePcmAudioCapture";

type UseAudioCaptureOptions = {
  onChunk: (base64: string) => void;
  chunkIntervalMs?: number;
};

export function useAudioCapture({ onChunk }: UseAudioCaptureOptions) {
  const { capturing, start, stop } = usePcmAudioCapture({
    onChunk: (chunk) => {
      onChunk(chunk.data);
    },
  });

  return { capturing, start, stop };
}
