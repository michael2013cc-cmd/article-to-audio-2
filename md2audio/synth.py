#!/usr/bin/env python3
"""Text-to-speech through Microsoft Edge's neural voices (via edge-tts).

One request per chapter. The endpoint is a free public service with no
guarantees, so every call is wrapped in a retry loop with backoff.
"""

from __future__ import annotations

import asyncio
import os
import time

import edge_tts

DEFAULT_VOICE = "zh-CN-YunyangNeural"  # news-anchor style, steady for long-form
DEFAULT_RATE = "-6%"  # a slow, comfortable pace for spoken numbers and lists

MAX_ATTEMPTS = 5
BACKOFF = 5.0


async def _speak(text: str, path: str, voice: str, rate: str) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(path)


def synth_text(
    text: str,
    path: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    attempts: int = MAX_ATTEMPTS,
) -> str:
    """Synthesize one block of text to an mp3 file. Retries on network faults."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            asyncio.run(_speak(text, path, voice, rate))
            if not os.path.getsize(path):
                raise RuntimeError("empty audio returned")
            return path
        except Exception as exc:  # noqa: BLE001 - endpoint fails in many ways
            last = exc
            print(f"  synth attempt {attempt}/{attempts} failed: {exc!r}", flush=True)
            if attempt < attempts:
                time.sleep(BACKOFF)
    raise RuntimeError(f"TTS failed after {attempts} attempts: {last}")


def synth_chapters(
    chapters,
    workdir: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    skip_existing: bool = False,
) -> list[str]:
    """Synthesize each chapter to ``workdir/raw_<n>.mp3``.

    ``skip_existing`` makes the run resumable after a dropped connection.
    """
    os.makedirs(workdir, exist_ok=True)
    paths = []
    for i, ch in enumerate(chapters):
        path = os.path.join(workdir, f"raw_{i}.mp3")
        if skip_existing and os.path.exists(path) and os.path.getsize(path):
            print(f"[{i}] {ch.title}: kept existing audio", flush=True)
        else:
            t0 = time.time()
            synth_text(ch.body, path, voice, rate)
            print(
                f"[{i}] {ch.title}: {os.path.getsize(path) // 1024} KiB "
                f"in {time.time() - t0:.0f}s",
                flush=True,
            )
        paths.append(path)
    return paths
