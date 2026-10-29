#!/usr/bin/env python3
"""Write ID3v2.4 chapter frames (CHAP/CTOC) and basic tags into the mp3.

Chapters are what make an hour-long lecture navigable: the player shows a
list and jumps per section instead of forcing the listener to scrub.

Two API traps worth remembering, both of which cost real time:
  * text frames take ``text=``, not ``desc=`` (``desc=`` silently yields an
    empty frame list);
  * save with ``v2_version=4`` - there is no ``v2_4=`` keyword.

A third, harmless one: mutagen upgrades the v2.3 ``TYER`` frame to ``TDRC``
when saving v2.4, so read the year back as ``TDRC``.
"""

from __future__ import annotations

from mutagen.id3 import CHAP, CTOC, TALB, TCON, TIT2, TPE1, TRCK, TYER, ID3


def _text_frame(cls, value: str):
    return cls(encoding=3, text=value)


def write_chapters(
    path: str,
    anchors: list[dict],
    title: str | None = None,
    album: str | None = None,
    artist: str | None = None,
    year: str | None = None,
) -> None:
    """Tag ``path`` with a chapter table of contents.

    ``anchors`` is a list of ``{"start": float, "sec": float, "title": str}``
    in seconds, measured on the final concatenated file.
    """
    tags = ID3()
    tags.clear()

    if title:
        tags.add(_text_frame(TIT2, title))
    if album:
        tags.add(_text_frame(TALB, album))
    if artist:
        tags.add(_text_frame(TPE1, artist))
    tags.add(_text_frame(TCON, "Education"))
    tags.add(_text_frame(TRCK, "1/1"))
    if year:
        tags.add(_text_frame(TYER, year))

    ids = []
    for i, ch in enumerate(anchors):
        cid = f"C{i:02d}"
        kid = f"K{i:02d}"
        ids.append(kid)
        start_ms = int(round(ch["start"] * 1000))
        end_ms = int(round((ch["start"] + ch["sec"]) * 1000))
        tags.add(CHAP(
            element_id=cid,
            start_time=start_ms,
            start_offset=None,
            end_time=end_ms,
            end_offset=None,
            sub_frames={},
        ))
        tags.add(CTOC(element_id=kid, is_top=False, child=[], indent=1))

    tags.add(CTOC(element_id="TOC", is_top=True, child=ids, indent=0))
    tags.save(path, v2_version=4)


def read_chapters(path: str) -> list[tuple[str, int, int]]:
    """Read back (element_id, start_ms, end_ms) - used to verify the write."""
    tags = ID3(path)
    out = []
    for key in sorted(k for k in tags.keys() if k.startswith("CHAP:")):
        frame = tags[key]
        out.append((key.split(":", 1)[1], frame.start_time, frame.end_time))
    return out
