"""Turn user-supplied URLs into safe iframe ``src`` values.

Only whitelisted hosts are ever embedded; anything else returns ``None`` and the
template simply doesn't render an iframe (the link may still be shown as text).
"""

import re
from urllib.parse import parse_qs, urlsplit

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}
FALSTAD_HOSTS = {"falstad.com", "www.falstad.com"}
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{6,15}$")


def _parts(url):
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    return parts


def youtube_embed_url(url):
    parts = _parts(url)
    if parts is None:
        return None
    host, video_id = parts.hostname.lower(), None
    if host == "youtu.be":
        video_id = parts.path.lstrip("/").split("/")[0]
    elif host in YOUTUBE_HOSTS:
        if parts.path.startswith("/embed/"):
            video_id = parts.path.split("/")[2] if len(parts.path.split("/")) > 2 else None
        elif parts.path == "/watch":
            video_id = (parse_qs(parts.query).get("v") or [None])[0]
    if video_id and _VIDEO_ID.match(video_id):
        # nocookie domain: no tracking cookies until the video is played.
        return f"https://www.youtube-nocookie.com/embed/{video_id}"
    return None


def falstad_embed_url(url):
    parts = _parts(url)
    if parts is None or parts.hostname.lower() not in FALSTAD_HOSTS or parts.port not in (None, 80, 443):
        return None
    return parts._replace(scheme="https", netloc=parts.hostname.lower()).geturl()
