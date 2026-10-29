#!/usr/bin/env python3
"""md2audio: turn a written document into a chaptered, phone-loud mp3.

Modules are usable individually (``synth``, ``audio``, ``tags``, ``verify``,
``transcript``, ``audit``) or together through ``pipeline.run``.
"""

from . import audio, audit, pipeline, script, synth, tags, transcript, verify
from .script import Chapter, dump, load, parse

__all__ = [
    "Chapter", "audio", "audit", "dump", "load", "parse",
    "pipeline", "script", "synth", "tags", "transcript", "verify",
]

__version__ = "0.1.0"
