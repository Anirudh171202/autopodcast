"""Text-to-speech via OpenAI's gpt-4o-mini-tts.

Chunks the script at paragraph boundaries (the TTS endpoint has a per-request
character limit well below a 10-minute script) and concatenates the pieces
with a short silence between them. Requires ffmpeg on PATH (pydub shells out
to it) — installed by default on GitHub Actions' ubuntu-latest runner; on a
Mac, `brew install ffmpeg`.
"""

import os
import tempfile

from openai import OpenAI
from pydub import AudioSegment

from . import config

MAX_CHARS = 3500
PAUSE_MS = 350


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if current and len(current) + len(p) + 2 > max_chars:
            chunks.append(current)
            current = p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return chunks


def synthesize(
    script_text: str,
    output_path: str,
    model: str = config.TTS_MODEL,
    voice: str = config.TTS_VOICE,
    instructions: str = config.TTS_INSTRUCTIONS,
) -> str:
    client = OpenAI()
    chunks = chunk_text(script_text)
    if not chunks:
        raise ValueError("Nothing to synthesize — script_text is empty.")

    with tempfile.TemporaryDirectory() as tmpdir:
        segments = []
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(tmpdir, f"chunk_{i:03d}.mp3")
            kwargs = {"model": model, "voice": voice, "input": chunk, "response_format": "mp3"}
            if instructions:
                kwargs["instructions"] = instructions
            with client.audio.speech.with_streaming_response.create(**kwargs) as response:
                response.stream_to_file(chunk_path)
            segments.append(AudioSegment.from_mp3(chunk_path))

        combined = segments[0]
        pause = AudioSegment.silent(duration=PAUSE_MS)
        for seg in segments[1:]:
            combined += pause + seg

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined.export(output_path, format="mp3", bitrate="96k")

    return output_path
