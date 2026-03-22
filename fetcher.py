import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from ytmusicapi import YTMusic


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
        if resource.lower() != "playlist":
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


def _extract_playlist_id_from_spotify_url(url: str) -> str:
    parsed = urlparse(url)
    # path is like /playlist/<id>
    parts = parsed.path.strip("/").split("/")
    return parts[1] if len(parts) >= 2 else ""


def fetch_spotify(url: str, client_id: Optional[str], client_secret: Optional[str]) -> dict:
    """Fetch tracks from a Spotify playlist URL.

    Returns: {"name": str, "playlist_id": str, "tracks": list[{"title": str, "artist": str}]}
    """
    if not client_id:
        raise FetchError(
            "SPOTIFY_CLIENT_ID is not set. Add it to your .env file."
        )
    if not client_secret:
        raise FetchError(
            "SPOTIFY_CLIENT_SECRET is not set. Add it to your .env file."
        )

    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth)

    playlist_id = _extract_playlist_id_from_spotify_url(url)

    try:
        data = sp.playlist(playlist_id)
    except spotipy.SpotifyException as e:
        if e.http_status in (403, 404):
            raise FetchError(
                f"Spotify playlist not found or is private: {url}"
            ) from e
        raise FetchError(f"Spotify API error: {e}") from e

    raw_name = data.get("name", "")
    pid = data.get("id", playlist_id)
    sanitized_name = sanitize_playlist_name(raw_name, fallback_id=pid)

    tracks = []
    items = data["tracks"]["items"]
    while True:
        for item in items:
            track = item.get("track")
            if not track:
                continue
            title = track.get("name", "")
            artists = track.get("artists", [])
            artist = artists[0]["name"] if artists else ""
            tracks.append({"title": title, "artist": artist})

        next_page = data["tracks"].get("next")
        if not next_page:
            break
        data["tracks"] = sp.next(data["tracks"])
        items = data["tracks"]["items"]

    return {"name": sanitized_name, "playlist_id": pid, "tracks": tracks}


def _extract_playlist_id_from_ytm_url(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    ids = qs.get("list", [])
    return ids[0] if ids else ""


def fetch_youtube_music(url: str) -> dict:
    """Fetch tracks from a YouTube Music playlist URL.

    Returns: {"name": str, "playlist_id": str, "tracks": list[{"title": str, "artist": str}]}
    """
    playlist_id = _extract_playlist_id_from_ytm_url(url)
    if not playlist_id:
        raise FetchError(f"Invalid YouTube Music URL (missing playlist ID): {url}")
    ytm = YTMusic()
    try:
        data = ytm.get_playlist(playlist_id, limit=None)
    except Exception as e:
        raise FetchError(f"YouTube Music API error: {e}") from e

    if not data:
        raise FetchError(f"YouTube Music playlist not found or inaccessible: {url}")

    raw_name = data.get("title", "")
    pid = data.get("id", playlist_id)
    sanitized_name = sanitize_playlist_name(raw_name, fallback_id=pid)

    tracks = []
    for item in data.get("tracks", []):
        title = item.get("title", "")
        artists = item.get("artists", [])
        artist = artists[0]["name"] if artists else ""
        tracks.append({"title": title, "artist": artist})

    return {"name": sanitized_name, "playlist_id": pid, "tracks": tracks}
