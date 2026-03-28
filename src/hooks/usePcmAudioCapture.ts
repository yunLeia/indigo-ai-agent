"use client";

import { useCallback, useRef, useState } from "react";

export type PcmAudioChunk = {
  data: string;
  format: "pcm16";
  sample_rate_hz: 16000;
};

type UsePcmAudioCaptureOptions = {
  onChunk: (chunk: PcmAudioChunk) => void;
  frameSize?: number;
  targetSampleRate?: 16000;
  rmsThreshold?: number;
  minActiveFrames?: number;
};

function floatTo16BitPcm(input: Float32Array) {
  const output = new Int16Array(input.length);

  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i] ?? 0));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }

  return new Uint8Array(output.buffer);
}

function downsampleBuffer(
  buffer: Float32Array,
  sourceRate: number,
  targetRate: number,
) {
  if (sourceRate === targetRate) {
    return buffer;
  }

  const ratio = sourceRate / targetRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);

  let offsetResult = 0;
  let offsetBuffer = 0;

  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0;
    let count = 0;

    for (
      let i = offsetBuffer;
      i < nextOffsetBuffer && i < buffer.length;
      i += 1
    ) {
      accum += buffer[i] ?? 0;
      count += 1;
    }

    result[offsetResult] = count > 0 ? accum / count : 0;
    offsetResult += 1;
    offsetBuffer = nextOffsetBuffer;
  }

  return result;
}

function bytesToBase64(bytes: Uint8Array) {
  let binary = "";

  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i] ?? 0);
  }

  return btoa(binary);
}

function getRmsLevel(buffer: Float32Array) {
  if (buffer.length === 0) {
    return 0;
  }

  let sumSquares = 0;
  for (let i = 0; i < buffer.length; i += 1) {
    const sample = buffer[i] ?? 0;
    sumSquares += sample * sample;
  }

  return Math.sqrt(sumSquares / buffer.length);
}

export function usePcmAudioCapture({
  onChunk,
  frameSize = 4096,
  targetSampleRate = 16000,
  rmsThreshold = 0.02,
  minActiveFrames = 2,
}: UsePcmAudioCaptureOptions) {
  const [capturing, setCapturing] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const activeFrameCountRef = useRef(0);

  const stop = useCallback(() => {
    processorNodeRef.current?.disconnect();
    sourceNodeRef.current?.disconnect();

    if (audioContextRef.current) {
      void audioContextRef.current.close();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }

    processorNodeRef.current = null;
    sourceNodeRef.current = null;
    audioContextRef.current = null;
    streamRef.current = null;
    activeFrameCountRef.current = 0;
    setCapturing(false);
  }, []);

  const start = useCallback(async () => {
    if (capturing) {
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        noiseSuppression: true,
        echoCancellation: true,
      },
    });

    const AudioContextCtor =
      window.AudioContext ||
      // @ts-expect-error webkit fallback for Safari
      window.webkitAudioContext;

    const audioContext = new AudioContextCtor();
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(frameSize, 1, 1);

    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const rms = getRmsLevel(input);

      if (rms < rmsThreshold) {
        activeFrameCountRef.current = 0;
        return;
      }

      activeFrameCountRef.current += 1;
      if (activeFrameCountRef.current < minActiveFrames) {
        return;
      }

      const downsampled = downsampleBuffer(
        input,
        audioContext.sampleRate,
        targetSampleRate,
      );
      const pcmBytes = floatTo16BitPcm(downsampled);

      onChunk({
        data: bytesToBase64(pcmBytes),
        format: "pcm16",
        sample_rate_hz: 16000,
      });
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    streamRef.current = stream;
    audioContextRef.current = audioContext;
    sourceNodeRef.current = source;
    processorNodeRef.current = processor;
    activeFrameCountRef.current = 0;
    setCapturing(true);
  }, [
    capturing,
    frameSize,
    minActiveFrames,
    onChunk,
    rmsThreshold,
    targetSampleRate,
  ]);

  return { capturing, start, stop };
}
