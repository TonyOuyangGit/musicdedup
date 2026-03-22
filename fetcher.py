import re
from urllib.parse import urlparse


class FetchError(Exception):
    pass


def detect_source(url: str) -> str:
    """Return 'spotify' or 'youtube_music', or raise FetchError."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise FetchError(f"Unrecognized playlist URL: {url!r}")

    host = parsed.netloc.lower()

    if "open.spotify.com" in host:
        path = parsed.path.lstrip("/")
        resource = path.split("/")[0] if path else ""
        if resource != "playlist":
            raise FetchError(
                f"Spotify URL is not a playlist (got {resource!r}): {url}"
            )
        return "spotify"

    if "music.youtube.com" in host:
        return "youtube_music"

    raise FetchError(f"Unrecognized playlist URL: {url!r}")


def sanitize_playlist_name(name: str, fallback_id: str = "") -> str:
    """Sanitize a playlist name for use as a filename component."""
    sanitized = name.lower()
    sanitized = re.sub(r"[^a-z0-9]+", "-", sanitized)
    sanitized = sanitized[:50]
    sanitized = sanitized.rstrip("-")
    if not sanitized:
        return fallback_id
    return sanitized
