"""Video allow-list.

The rule: never put the author's URL into the page. Parse it, pull out the
one piece we need (a video ID), check that piece against a strict pattern,
and build the embed URL ourselves from a hard-coded template.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlparse

YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIMEO_ID = re.compile(r"^[0-9]{1,12}$")
LOCAL_VIDEO_EXTENSIONS = {".mp4", ".webm"}

YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "youtu.be"}
VIMEO_HOSTS = {"vimeo.com", "player.vimeo.com"}


def resolve_video(src: str) -> tuple[str, str]:
    """Return (provider, embed_url) or raise ValueError if not allowed."""
    src = src.strip()

    if src.startswith("media/"):
        return "local", "/" + safe_media_path(src, LOCAL_VIDEO_EXTENSIONS)

    url = urlparse(src)
    if url.scheme != "https":
        raise ValueError("video URL must use https (or be a media/ file)")

    host = (url.hostname or "").lower().removeprefix("www.")
    parts = [p for p in url.path.split("/") if p]

    if host in YOUTUBE_HOSTS:
        if host == "youtu.be":
            video_id = parts[0] if parts else ""
        elif parts[:1] == ["watch"]:
            video_id = parse_qs(url.query).get("v", [""])[0]
        elif parts[:1] in (["embed"], ["shorts"]) and len(parts) > 1:
            video_id = parts[1]
        else:
            video_id = ""
        if not YOUTUBE_ID.match(video_id):
            raise ValueError("could not find a valid YouTube video ID")
        return "youtube", f"https://www.youtube-nocookie.com/embed/{video_id}"

    if host in VIMEO_HOSTS:
        video_id = parts[-1] if parts else ""
        if not VIMEO_ID.match(video_id):
            raise ValueError("could not find a valid Vimeo video ID")
        return "vimeo", f"https://player.vimeo.com/video/{video_id}"

    raise ValueError(f"video provider not allowed: {host or src!r}")


def safe_media_path(src: str, allowed_extensions: set[str] | None = None) -> str:
    """Accept only plain paths inside media/, e.g. media/photo.jpg."""
    path = PurePosixPath(src)
    if path.is_absolute() or ".." in path.parts or path.parts[:1] != ("media",):
        raise ValueError("media paths must stay inside media/")
    if len(path.parts) < 2:
        raise ValueError("media path is missing a file name")
    if allowed_extensions and path.suffix.lower() not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"file type not allowed here (use {allowed})")
    return str(path)
