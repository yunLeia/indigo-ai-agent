from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.contracts import AudioChunkMessage


@dataclass
class DecodedAudioChunk:
    raw_bytes: bytes
    mime_type: str
    sample_rate_hz: Optional[int] = None
    encoding: Optional[str] = None


class BaseAudioDecoder:
    def decode(self, chunk: AudioChunkMessage) -> DecodedAudioChunk:
        raise NotImplementedError


class Pcm16Decoder(BaseAudioDecoder):
    def decode(self, chunk: AudioChunkMessage) -> DecodedAudioChunk:
        if chunk.sample_rate_hz and chunk.sample_rate_hz != 16000:
            raise RuntimeError(
                f"pcm16 live input must use 16000Hz. Received {chunk.sample_rate_hz}Hz."
            )

        return DecodedAudioChunk(
            raw_bytes=base64.b64decode(chunk.data),
            mime_type="audio/pcm;rate=16000",
            sample_rate_hz=16000,
            encoding="pcm_s16le",
        )


class BrowserMediaRecorderDecoder(BaseAudioDecoder):
    """
    Current browser capture path sends `audio/webm` chunks encoded as base64.

    For now we preserve the bytes and treat them as an opaque blob because the
    demo runtime does not inspect them.

    Next step:
    - decode webm/opus into raw PCM
    - normalize to the input format expected by Gemini Live
    """

    def decode(self, chunk: AudioChunkMessage) -> DecodedAudioChunk:
        return DecodedAudioChunk(
            raw_bytes=base64.b64decode(chunk.data),
            mime_type="audio/webm",
        )


def build_audio_decoder(chunk: AudioChunkMessage) -> BaseAudioDecoder:
    if chunk.format == "pcm16" or settings.audio_input_mode == "pcm16":
        return Pcm16Decoder()

    return BrowserMediaRecorderDecoder()
