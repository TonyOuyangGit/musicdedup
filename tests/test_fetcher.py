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
