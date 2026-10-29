#!/usr/bin/env python3
"""End-to-end pipeline: listening script -> tagged mp3 + transcript.

Stages, each of which writes into ``workdir`` so a crashed run can resume:

    script.txt
      -> raw_<i>.mp3      synthesize one chapter per request
      -> norm_<i>.mp3     loudness + fixed codec parameters
      -> <output>.mp3     lossless concatenation
      -> (tagged)         ID3v2.4 CHAP/CTOC chapter table
      -> <output>.txt     timestamped transcript

Anchors are measured on the normalized parts, never on the raw ones: the
limiter and the encoder shift durations by a few tens of milliseconds per
chapter, and that drift accumulates into visibly wrong jump points.
"""

from __future__ import annotations

import os
import shutil

from . import audio, script as scriptmod, synth, tags, transcript as transcriptmod, verify


def run(
    script_path: str,
    output: str,
    *,
    workdir: str | None = None,
    voice: str = synth.DEFAULT_VOICE,
    rate: str = synth.DEFAULT_RATE,
    bitrate: str = audio.BITRATE,
    title: str | None = None,
    album: str | None = None,
    artist: str | None = None,
    year: str | None = None,
    resume: bool = False,
    write_transcript: bool = True,
    quiet: bool = False,
) -> dict:
    """Build the audio file. Returns the verify report plus the paths written."""

    def say(*args) -> None:
        if not quiet:
            print(*args, flush=True)

    chapters = scriptmod.load(script_path)
    workdir = workdir or (os.path.splitext(os.path.abspath(output))[0] + "_work")
    os.makedirs(workdir, exist_ok=True)
    say(f"{len(chapters)} chapters -> {output}  (workdir {workdir})")

    say("\n[1/5] synthesize")
    raw = synth.synth_chapters(chapters, workdir, voice, rate, skip_existing=resume)

    say("\n[2/5] normalise loudness")
    norm = audio.normalize_chapters(raw, workdir, bitrate=bitrate)

    anchors = []
    pos = 0.0
    for ch, part in zip(chapters, norm):
        sec = audio.duration(part)
        anchors.append({"start": pos, "sec": sec, "title": ch.title})
        pos += sec

    say("\n[3/5] concat")
    joined = os.path.join(workdir, "joined.mp3")
    audio.concat(norm, joined, workdir)
    total = sum(a["sec"] for a in anchors)
    say(f"      {total / 60:.1f} min of audio, {os.path.getsize(joined) // 1024 // 1024} MiB")

    # copy the audio into place *before* tagging: mutagen only patches an
    # existing file, and saving a tag onto a missing path produces a
    # tag-only stub that looks like a success.
    shutil.copyfile(joined, output)

    say("\n[4/5] write chapter tags")
    tags.write_chapters(
        output,
        anchors,
        title=title or os.path.splitext(os.path.basename(output))[0],
        album=album,
        artist=artist,
        year=year,
    )

    say("\n[5/5] verify")
    report = verify.check_file(output, expect_chapters=len(chapters))
    say(
        f"      {report['integrated_lufs']} LUFS, true peak {report['true_peak_dbfs']} dBFS, "
        f"flat factor {report['flat_factor']}, chapters {report['chapters']}"
    )
    if not report["ok"]:
        for problem in report["problems"]:
            say(f"      !! {problem}")
    else:
        say("      ok")

    transcript_path = None
    if write_transcript:
        transcript_path = os.path.splitext(output)[0] + ".txt"
        text = transcriptmod.build_transcript(
            chapters,
            anchors,
            audio_name=os.path.basename(output),
            title=title or "",
        )
        transcriptmod.write_transcript(transcript_path, text)
        say(f"      transcript -> {transcript_path}")

    report.update({
        "output": output,
        "transcript": transcript_path,
        "anchors": anchors,
        "duration_sec": total,
        "workdir": workdir,
    })
    return report
