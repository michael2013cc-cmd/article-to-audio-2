#!/usr/bin/env python3
"""Command line: ``python -m md2audio make examples/sample.txt -o out/sample.mp3``"""

from __future__ import annotations

import argparse
import json
import sys

from . import audit, pipeline, script, synth, verify


def _cmd_make(args: argparse.Namespace) -> int:
    report = pipeline.run(
        args.script,
        args.output,
        workdir=args.workdir,
        voice=args.voice,
        rate=args.rate,
        bitrate=args.bitrate,
        title=args.title,
        album=args.album,
        artist=args.artist,
        year=args.year,
        resume=args.resume,
        write_transcript=not args.no_transcript,
    )
    if not report["ok"]:
        print("\nfinished, but the file did not pass verification:", file=sys.stderr)
        for problem in report["problems"]:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    report = verify.check_file(args.file, expect_chapters=args.chapters)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def _cmd_parse(args: argparse.Namespace) -> int:
    chapters = script.load(args.script)
    if args.json:
        print(json.dumps(
            [{"id": c.id, "title": c.title, "chars": len(c.body)} for c in chapters],
            ensure_ascii=False, indent=2,
        ))
    else:
        for i, c in enumerate(chapters):
            print(f"{i:2d}  @{c.id:<4} {len(c.body):>6} chars  {c.title}")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    report = audit.audit(args.script, args.source)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["problems"] and not args.force_ok:
        print("\nreview the flagged items before synthesizing.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    # md2audio/__init__.py already forced UTF-8 on stdout/stderr, because a
    # cp950 console cannot encode a chapter title and would kill the run.
    parser = argparse.ArgumentParser(
        prog="md2audio",
        description="listening script -> chaptered mp3",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("make", help="build the mp3 (and the transcript)")
    p.add_argument("script", help="path to the @@ID|Title script")
    p.add_argument("-o", "--output", required=True, help="output .mp3")
    p.add_argument("--workdir", help="scratch dir (default: <output>_work)")
    p.add_argument("--voice", default=synth.DEFAULT_VOICE)
    p.add_argument("--rate", default=synth.DEFAULT_RATE)
    p.add_argument("--bitrate", default="64k")
    p.add_argument("--title", help="ID3 title; also the transcript heading")
    p.add_argument("--album")
    p.add_argument("--artist")
    p.add_argument("--year")
    p.add_argument("--resume", action="store_true",
                   help="keep already-synthesized chapters in the workdir")
    p.add_argument("--no-transcript", action="store_true")
    p.set_defaults(func=_cmd_make)

    p = sub.add_parser("check", help="measure an existing mp3")
    p.add_argument("file")
    p.add_argument("--chapters", type=int, help="expected chapter count")
    p.set_defaults(func=_cmd_check)

    p = sub.add_parser("parse", help="show the chapter table of a script")
    p.add_argument("script")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_parse)

    p = sub.add_parser("audit", help="flag numbers and stray tokens in a script")
    p.add_argument("script")
    p.add_argument("--source", help="original document to diff numbers against")
    p.add_argument("--force-ok", action="store_true", help="always exit 0")
    p.set_defaults(func=_cmd_audit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
