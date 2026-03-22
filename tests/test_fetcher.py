import pytest
from fetcher import detect_source, FetchError

# --- URL detection ---

def test_detects_spotify_playlist():
    url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    assert detect_source(url) == "spotify"


def test_detects_youtube_music_playlist():
    url = "https://music.youtube.com/playlist?list=PLxxxxxxx"
    assert detect_source(url) == "youtube_music"


def test_raises_on_unrecognized_url():
    with pytest.raises(FetchError, match="Unrecognized playlist URL"):
        detect_source("https://soundcloud.com/artist/track")


def test_raises_on_spotify_track_url():
    with pytest.raises(FetchError, match="not a playlist"):
        detect_source("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")


def test_raises_on_spotify_album_url():
    with pytest.raises(FetchError, match="not a playlist"):
        detect_source("https://open.spotify.com/album/4cOdK2wGLETKBW3PvgPWqT")


def test_raises_on_spotify_artist_url():
    with pytest.raises(FetchError, match="not a playlist"):
        detect_source("https://open.spotify.com/artist/4cOdK2wGLETKBW3PvgPWqT")


def test_raises_on_plain_string():
    with pytest.raises(FetchError, match="Unrecognized playlist URL"):
        detect_source("not a url at all")


# --- Playlist name sanitization ---
from fetcher import sanitize_playlist_name

def test_sanitize_lowercases():
    assert sanitize_playlist_name("My Wedding") == "my-wedding"


def test_sanitize_replaces_spaces_and_symbols():
    # regex collapses consecutive non-alphanumeric chars into one hyphen
    assert sanitize_playlist_name("Top 100! Hits") == "top-100-hits"


def test_sanitize_truncates_to_50_chars():
    long_name = "a" * 60
    result = sanitize_playlist_name(long_name)
    assert len(result) <= 50


def test_sanitize_strips_trailing_hyphens_after_truncation():
    # 49 a's + a symbol that becomes a hyphen = 50 chars ending in '-'
    name = "a" * 49 + "!"
    result = sanitize_playlist_name(name)
    assert not result.endswith("-")


def test_sanitize_falls_back_to_playlist_id_when_empty():
    result = sanitize_playlist_name("", fallback_id="abc123")
    assert result == "abc123"


def test_sanitize_falls_back_to_playlist_id_when_all_symbols():
    result = sanitize_playlist_name("!!!---!!!", fallback_id="abc123")
    assert result == "abc123"
