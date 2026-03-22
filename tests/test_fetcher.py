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


# --- Spotify fetcher ---
from unittest.mock import MagicMock, patch
from fetcher import fetch_spotify

def test_fetch_spotify_raises_when_credentials_missing():
    with pytest.raises(FetchError, match="SPOTIFY_CLIENT_ID"):
        fetch_spotify(
            "https://open.spotify.com/playlist/abc123",
            client_id=None,
            client_secret="secret",
        )


def test_fetch_spotify_raises_when_secret_missing():
    with pytest.raises(FetchError, match="SPOTIFY_CLIENT_SECRET"):
        fetch_spotify(
            "https://open.spotify.com/playlist/abc123",
            client_id="id",
            client_secret=None,
        )


def test_fetch_spotify_returns_tracks_and_name(mocker):
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {
        "name": "Wedding Mix",
        "id": "abc123",
        "tracks": {
            "items": [
                {"track": {"name": "Perfect", "artists": [{"name": "Ed Sheeran"}]}},
                {"track": {"name": "Thinking Out Loud", "artists": [{"name": "Ed Sheeran"}]}},
            ],
            "next": None,
        },
    }
    mocker.patch("fetcher.spotipy.Spotify", return_value=mock_sp)
    mocker.patch("fetcher.SpotifyClientCredentials", return_value=MagicMock())

    result = fetch_spotify(
        "https://open.spotify.com/playlist/abc123",
        client_id="id",
        client_secret="secret",
    )
    assert result["name"] == "wedding-mix"
    assert result["playlist_id"] == "abc123"
    assert len(result["tracks"]) == 2
    assert result["tracks"][0] == {"title": "Perfect", "artist": "Ed Sheeran"}


def test_fetch_spotify_preserves_duplicate_tracks(mocker):
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {
        "name": "Mix",
        "id": "abc123",
        "tracks": {
            "items": [
                {"track": {"name": "Perfect", "artists": [{"name": "Ed Sheeran"}]}},
                {"track": {"name": "Perfect", "artists": [{"name": "Ed Sheeran"}]}},
            ],
            "next": None,
        },
    }
    mocker.patch("fetcher.spotipy.Spotify", return_value=mock_sp)
    mocker.patch("fetcher.SpotifyClientCredentials", return_value=MagicMock())

    result = fetch_spotify(
        "https://open.spotify.com/playlist/abc123",
        client_id="id",
        client_secret="secret",
    )
    assert len(result["tracks"]) == 2


def test_fetch_spotify_raises_on_404(mocker):
    import spotipy
    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = spotipy.SpotifyException(404, -1, "Not found")
    mocker.patch("fetcher.spotipy.Spotify", return_value=mock_sp)
    mocker.patch("fetcher.SpotifyClientCredentials", return_value=MagicMock())

    with pytest.raises(FetchError, match="not found or is private"):
        fetch_spotify(
            "https://open.spotify.com/playlist/abc123",
            client_id="id",
            client_secret="secret",
        )


def test_fetch_spotify_handles_pagination(mocker):
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {
        "name": "Large Playlist",
        "id": "abc123",
        "tracks": {
            "items": [{"track": {"name": "Track 1", "artists": [{"name": "Artist 1"}]}}],
            "next": "https://api.spotify.com/v1/playlists/abc123/tracks?offset=1",
        },
    }
    mock_sp.next.return_value = {
        "items": [{"track": {"name": "Track 2", "artists": [{"name": "Artist 2"}]}}],
        "next": None,
    }
    mocker.patch("fetcher.spotipy.Spotify", return_value=mock_sp)
    mocker.patch("fetcher.SpotifyClientCredentials", return_value=MagicMock())

    result = fetch_spotify(
        "https://open.spotify.com/playlist/abc123",
        client_id="id",
        client_secret="secret",
    )
    assert len(result["tracks"]) == 2
    assert result["tracks"][0] == {"title": "Track 1", "artist": "Artist 1"}
    assert result["tracks"][1] == {"title": "Track 2", "artist": "Artist 2"}
    mock_sp.next.assert_called_once()
