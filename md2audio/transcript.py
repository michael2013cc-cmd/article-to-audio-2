#!/usr/bin/env python3
"""Companion transcript with timestamps.

A long spoken lecture is hard to search by ear. Emitting the exact text that
was spoken, with a start time per chapter, gives the listener an index they
can grep - which paragraphs came from the source document and which were
added by the narrator, in particular.
"""

from __future__ import annotations


def clock(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def build_transcript(
    chapters,
    anchors: list[dict],
    *,
    audio_name: str,
    title: str = "",
    header_notes: list[str] | None = None,
    separator_width: int = 62,
) -> str:
    lines: list[str] = []
    total = anchors[-1]["start"] + anchors[-1]["sec"] if anchors else 0.0

    lines.append(title.strip())
    lines.append("")
    lines.append(f"对应音频：{audio_name}")
    lines.append(f"总时长：{clock(total)}（约 {total / 60:.0f} 分钟）")
    lines.append(f"章节标记：共 {len(anchors)} 节，已写入 MP3 的 ID3v2.4 CHAP/CTOC 标签。")
    for note in header_notes or []:
        lines.append(note)

    lines += ["", "【时间点索引】"]
    for i, ch in enumerate(anchors):
        lines.append(f"  {clock(ch['start'])}  第{i + 1}节　{ch['title']}")

    lines += ["", "=" * separator_width]
    for i, ch in enumerate(anchors):
        lines += ["", f"【{clock(ch['start'])}】第{i + 1}节　{ch['title']}"
                      f"　（本节约 {clock(ch['sec'])}）", ""]
        for para in chapters[i].body.split("\n\n"):
            para = para.strip()
            if para:
                lines += [para, ""]
        lines.append("-" * separator_width)

    return "\n".join(lines)


def write_transcript(path: str, text: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path
