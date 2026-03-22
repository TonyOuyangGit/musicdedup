# musicdedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that compares a Spotify or YouTube Music playlist against a local music library and reports which tracks are present and which are missing.

**Architecture:** A single entry-point script (`musicdedup.py`) orchestrates four focused modules: `fetcher` (playlist data from API), `scanner` (local library index), `matcher` (fuzzy comparison), and `reporter` (terminal + CSV output). Config is loaded centrally from `.env` / environment variables and validated at startup.

**Tech Stack:** Python 3.10+, spotipy, ytmusicapi, mutagen, rapidfuzz, python-dotenv, pytest

---

## File Structure

| File | Responsibility |
|---|---|
| `musicdedup.py` | CLI entry point: parse args, call modules in sequence, handle exits |
| `config.py` | Load and validate all env vars; raise on invalid config |
| `fetcher.py` | URL detection, Spotify fetch, YouTube Music fetch, name sanitization |
| `scanner.py` | Walk local library, read tags via mutagen, filename fallback |
| `matcher.py` | Build comparison strings, run WRatio fuzzy matching |
| `reporter.py` | Print terminal output, write CSV |
| `requirements.txt` | Pinned dependencies |
| `.env.example` | Template for user configuration |
| `.gitignore` | Exclude `.env`, `__pycache__`, venv |
| `README.md` | Setup and usage documentation |
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/test_config.py` | Config loading and validation tests |
| `tests/test_fetcher.py` | URL detection and playlist fetch tests (mocked APIs) |
| `tests/test_scanner.py` | Library scanner tests (temp files) |
| `tests/test_matcher.py` | Fuzzy matcher tests |
| `tests/test_reporter.py` | Terminal output and CSV export tests |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `requirements.txt`**

```
spotipy>=2.23.0
ytmusicapi>=1.3.0
mutagen>=1.47.0
rapidfuzz>=3.6.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create `.env.example`**

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
MUSIC_LIBRARY_PATH=/path/to/your/music/folder
MATCH_THRESHOLD=85
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
venv/
.venv/
*.csv
```

- [ ] **Step 4: Create `tests/conftest.py`** (empty for now, will add fixtures later)

```python
# shared pytest fixtures
```

- [ ] **Step 5: Create venv and install dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore tests/conftest.py
git commit -m "chore: project scaffolding"
```

---

### Task 2: Config Module

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
import os
import pytest
from config import load_config, ConfigError


def test_raises_when_library_path_not_set(monkeypatch):
    monkeypatch.delenv("MUSIC_LIBRARY_PATH", raising=False)
    with pytest.raises(ConfigError, match="MUSIC_LIBRARY_PATH is not configured"):
        load_config()


def test_raises_when_library_path_does_not_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path / "nonexistent"))
    with pytest.raises(ConfigError, match="does not exist"):
        load_config()


def test_raises_when_library_path_is_a_file(monkeypatch, tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(f))
    with pytest.raises(ConfigError, match="not a directory"):
        load_config()


def test_raises_when_threshold_is_not_an_integer(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("MATCH_THRESHOLD", "banana")
    with pytest.raises(ConfigError, match="MATCH_THRESHOLD must be an integer"):
        load_config()


def test_raises_when_threshold_out_of_range(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("MATCH_THRESHOLD", "101")
    with pytest.raises(ConfigError, match="between 0 and 100"):
        load_config()


def test_default_threshold_is_85(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    monkeypatch.delenv("MATCH_THRESHOLD", raising=False)
    cfg = load_config()
    assert cfg["threshold"] == 85


def test_returns_absolute_library_path(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    cfg = load_config()
    assert os.path.isabs(cfg["library_path"])


def test_accepts_relative_library_path(monkeypatch, tmp_path):
    # relative paths should be resolved to absolute
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", ".")
    cfg = load_config()
    assert os.path.isabs(cfg["library_path"])
    assert os.path.isdir(cfg["library_path"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv(override=False)


class ConfigError(Exception):
    pass


def load_config() -> dict:
    library_path = os.environ.get("MUSIC_LIBRARY_PATH")
    if not library_path:
        raise ConfigError("MUSIC_LIBRARY_PATH is not configured.")

    library_path = os.path.abspath(library_path)
    if not os.path.exists(library_path):
        raise ConfigError(f"MUSIC_LIBRARY_PATH does not exist: {library_path}")
    if not os.path.isdir(library_path):
        raise ConfigError(f"MUSIC_LIBRARY_PATH is not a directory: {library_path}")

    threshold_raw = os.environ.get("MATCH_THRESHOLD", "85")
    try:
        threshold = int(threshold_raw)
    except ValueError:
        raise ConfigError(f"MATCH_THRESHOLD must be an integer, got: {threshold_raw!r}")
    if not (0 <= threshold <= 100):
        raise ConfigError(f"MATCH_THRESHOLD must be between 0 and 100, got: {threshold}")

    return {
        "library_path": library_path,
        "threshold": threshold,
        "spotify_client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
        "spotify_client_secret": os.environ.get("SPOTIFY_CLIENT_SECRET"),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config loading and validation"
```

---

### Task 3: URL Detection

**Files:**
- Create: `fetcher.py` (URL detection portion only)
- Create: `tests/test_fetcher.py` (URL detection tests only)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fetcher.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_fetcher.py -v
```

Expected: `ModuleNotFoundError: No module named 'fetcher'`

- [ ] **Step 3: Implement URL detection in `fetcher.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: URL detection for Spotify and YouTube Music"
```

---

### Task 4: Playlist Name Sanitization

**Files:**
- Modify: `fetcher.py`
- Modify: `tests/test_fetcher.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fetcher.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_fetcher.py::test_sanitize_lowercases -v
```

Expected: `ImportError: cannot import name 'sanitize_playlist_name'`

- [ ] **Step 3: Implement `sanitize_playlist_name` in `fetcher.py`**

Append to `fetcher.py`:

```python
import re


def sanitize_playlist_name(name: str, fallback_id: str = "") -> str:
    """Sanitize a playlist name for use as a filename component."""
    sanitized = name.lower()
    sanitized = re.sub(r"[^a-z0-9]+", "-", sanitized)
    sanitized = sanitized[:50]
    sanitized = sanitized.rstrip("-")
    if not sanitized:
        return fallback_id
    return sanitized
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: all 13 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: playlist name sanitization"
```

---

### Task 5: Spotify Playlist Fetcher

**Files:**
- Modify: `fetcher.py`
- Modify: `tests/test_fetcher.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fetcher.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_fetcher.py::test_fetch_spotify_raises_when_credentials_missing -v
```

Expected: `ImportError: cannot import name 'fetch_spotify'`

- [ ] **Step 3: Implement `fetch_spotify` in `fetcher.py`**

Append to `fetcher.py`:

```python
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


def _extract_playlist_id_from_spotify_url(url: str) -> str:
    parsed = urlparse(url)
    # path is like /playlist/<id>
    parts = parsed.path.strip("/").split("/")
    return parts[1] if len(parts) >= 2 else ""


def fetch_spotify(url: str, client_id: str | None, client_secret: str | None) -> dict:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: Spotify playlist fetcher"
```

---

### Task 6: YouTube Music Playlist Fetcher

**Files:**
- Modify: `fetcher.py`
- Modify: `tests/test_fetcher.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_fetcher.py`:

```python
# --- YouTube Music fetcher ---
from fetcher import fetch_youtube_music

def test_fetch_youtube_music_returns_tracks_and_name(mocker):
    mock_ytm = MagicMock()
    mock_ytm.get_playlist.return_value = {
        "title": "First Dance Songs",
        "id": "PLxxx",
        "tracks": [
            {"title": "Can't Help Falling in Love", "artists": [{"name": "Elvis Presley"}]},
            {"title": "At Last", "artists": [{"name": "Etta James"}]},
        ],
    }
    mocker.patch("fetcher.YTMusic", return_value=mock_ytm)

    result = fetch_youtube_music("https://music.youtube.com/playlist?list=PLxxx")
    assert result["name"] == "first-dance-songs"
    assert len(result["tracks"]) == 2
    assert result["tracks"][0] == {
        "title": "Can't Help Falling in Love",
        "artist": "Elvis Presley",
    }


def test_fetch_youtube_music_raises_on_not_found(mocker):
    mock_ytm = MagicMock()
    mock_ytm.get_playlist.return_value = None
    mocker.patch("fetcher.YTMusic", return_value=mock_ytm)

    with pytest.raises(FetchError, match="not found or inaccessible"):
        fetch_youtube_music("https://music.youtube.com/playlist?list=PLxxx")


def test_fetch_youtube_music_preserves_duplicates(mocker):
    mock_ytm = MagicMock()
    mock_ytm.get_playlist.return_value = {
        "title": "Mix",
        "id": "PLxxx",
        "tracks": [
            {"title": "At Last", "artists": [{"name": "Etta James"}]},
            {"title": "At Last", "artists": [{"name": "Etta James"}]},
        ],
    }
    mocker.patch("fetcher.YTMusic", return_value=mock_ytm)

    result = fetch_youtube_music("https://music.youtube.com/playlist?list=PLxxx")
    assert len(result["tracks"]) == 2
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_fetcher.py::test_fetch_youtube_music_returns_tracks_and_name -v
```

Expected: `ImportError: cannot import name 'fetch_youtube_music'`

- [ ] **Step 3: Implement `fetch_youtube_music` in `fetcher.py`**

Append to `fetcher.py`:

```python
from ytmusicapi import YTMusic
from urllib.parse import parse_qs


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
    ytm = YTMusic()
    data = ytm.get_playlist(playlist_id, limit=None)

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_fetcher.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: YouTube Music playlist fetcher"
```

---

### Task 7: Library Scanner

**Files:**
- Create: `scanner.py`
- Create: `tests/test_scanner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scanner.py
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scanner import scan_library, SUPPORTED_EXTENSIONS


def make_music_file(directory: Path, filename: str) -> Path:
    """Create a dummy file with a supported extension."""
    path = directory / filename
    path.write_bytes(b"fake audio data")
    return path


def test_returns_empty_list_for_empty_folder(tmp_path):
    assert scan_library(str(tmp_path)) == []


def test_ignores_unsupported_file_extensions(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(b"img")
    (tmp_path / "notes.txt").write_text("x")
    assert scan_library(str(tmp_path)) == []


def test_reads_id3_tags_when_available(tmp_path, mocker):
    mp3 = make_music_file(tmp_path, "track.mp3")
    mock_tags = MagicMock()
    mock_tags.__getitem__ = MagicMock(side_effect=lambda k: {
        "TIT2": MagicMock(text=["Perfect"]),
        "TPE1": MagicMock(text=["Ed Sheeran"]),
    }[k])
    mock_tags.get = MagicMock(side_effect=lambda k, d=None: {
        "TIT2": MagicMock(text=["Perfect"]),
        "TPE1": MagicMock(text=["Ed Sheeran"]),
    }.get(k, d))
    mocker.patch("scanner.mutagen.File", return_value=mock_tags)

    results = scan_library(str(tmp_path))
    assert len(results) == 1
    assert results[0]["title"] == "Perfect"
    assert results[0]["artist"] == "Ed Sheeran"
    assert os.path.isabs(results[0]["filepath"])


def test_falls_back_to_filename_when_no_tags(tmp_path, mocker):
    make_music_file(tmp_path, "Ed Sheeran - Perfect.mp3")
    mocker.patch("scanner.mutagen.File", return_value=None)

    results = scan_library(str(tmp_path))
    assert results[0]["title"] == "Perfect"
    assert results[0]["artist"] == "Ed Sheeran"


def test_filename_fallback_no_hyphen_uses_full_stem_as_title(tmp_path, mocker):
    make_music_file(tmp_path, "Perfect.mp3")
    mocker.patch("scanner.mutagen.File", return_value=None)

    results = scan_library(str(tmp_path))
    assert results[0]["title"] == "Perfect"
    assert results[0]["artist"] == ""


def test_skips_file_and_warns_when_mutagen_raises(tmp_path, mocker, capsys):
    make_music_file(tmp_path, "bad.mp3")
    mocker.patch("scanner.mutagen.File", side_effect=Exception("corrupted"))

    results = scan_library(str(tmp_path))
    assert results == []
    captured = capsys.readouterr()
    assert "Warning" in captured.out or "Warning" in captured.err


def test_scans_subdirectories_recursively(tmp_path, mocker):
    sub = tmp_path / "subfolder"
    sub.mkdir()
    make_music_file(sub, "song.flac")
    mocker.patch("scanner.mutagen.File", return_value=None)

    results = scan_library(str(tmp_path))
    assert len(results) == 1


def test_supported_extensions_includes_expected_formats():
    for ext in [".mp3", ".flac", ".m4a", ".aiff", ".wav", ".ogg"]:
        assert ext in SUPPORTED_EXTENSIONS
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_scanner.py -v
```

Expected: `ModuleNotFoundError: No module named 'scanner'`

- [ ] **Step 3: Implement `scanner.py`**

```python
import os
import mutagen

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".aiff", ".wav", ".ogg"}

_SENTINEL = object()  # distinguishes "mutagen error" from "no tags"


def _read_tags(filepath: str):
    """Return {title, artist} from embedded tags, None if no tags, or _SENTINEL on error."""
    try:
        tags = mutagen.File(filepath, easy=True)
    except Exception as e:
        print(f"Warning: could not read tags for {filepath!r}: {e}", flush=True)
        return _SENTINEL

    if not tags:
        return None

    title = str(tags.get("title", [""])[0]).strip()
    artist = str(tags.get("artist", [""])[0]).strip()

    if not title and not artist:
        return None

    return {"title": title, "artist": artist}


def _parse_filename(filepath: str) -> dict:
    """Extract title and artist from filename stem."""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if " - " in stem:
        artist, _, title = stem.partition(" - ")
        return {"title": title.strip(), "artist": artist.strip()}
    return {"title": stem.strip(), "artist": ""}


def scan_library(library_path: str) -> list[dict]:
    """Walk library_path and return a list of {title, artist, filepath} dicts."""
    results = []
    for dirpath, _dirnames, filenames in os.walk(library_path):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            filepath = os.path.abspath(os.path.join(dirpath, filename))
            tags = _read_tags(filepath)
            if tags is _SENTINEL:
                # mutagen raised — skip this file entirely per spec
                continue
            if tags:
                entry = {**tags, "filepath": filepath}
            else:
                # no tags — fall back to filename parsing
                parsed = _parse_filename(filepath)
                entry = {**parsed, "filepath": filepath}
            results.append(entry)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scanner.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add scanner.py tests/test_scanner.py
git commit -m "feat: library scanner with tag reading and filename fallback"
```

---

### Task 8: Fuzzy Matcher

**Files:**
- Create: `matcher.py`
- Create: `tests/test_matcher.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_matcher.py
import pytest
from matcher import build_comparison_string, match_tracks, MatchResult


def test_comparison_string_with_artist():
    assert build_comparison_string("Ed Sheeran", "Perfect") == "Ed Sheeran - Perfect"


def test_comparison_string_without_artist():
    assert build_comparison_string("", "Perfect") == "Perfect"


def test_exact_match_is_found():
    playlist_track = {"title": "Perfect", "artist": "Ed Sheeran"}
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].status == "Found"
    assert results[0].matched_filepath == "/music/perfect.mp3"


def test_remix_is_matched():
    playlist_track = {"title": "Blinding Lights", "artist": "The Weeknd"}
    library = [
        {
            "title": "Blinding Lights (Radio Edit)",
            "artist": "The Weeknd",
            "filepath": "/music/blinding.mp3",
        }
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].status == "Found"


def test_unrelated_track_is_missing():
    playlist_track = {"title": "Bohemian Rhapsody", "artist": "Queen"}
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].status == "Missing"
    assert results[0].matched_filepath == ""


def test_empty_library_returns_all_missing():
    tracks = [
        {"title": "Perfect", "artist": "Ed Sheeran"},
        {"title": "At Last", "artist": "Etta James"},
    ]
    results = match_tracks(tracks, [], threshold=85)
    assert all(r.status == "Missing" for r in results)


def test_duplicate_playlist_entries_produce_separate_results():
    playlist = [
        {"title": "Perfect", "artist": "Ed Sheeran"},
        {"title": "Perfect", "artist": "Ed Sheeran"},
    ]
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks(playlist, library, threshold=85)
    assert len(results) == 2


def test_tie_uses_first_in_scan_order():
    playlist_track = {"title": "Perfect", "artist": "Ed Sheeran"}
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/first.mp3"},
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/second.mp3"},
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].matched_filepath == "/music/first.mp3"


def test_local_track_without_artist_can_still_match():
    playlist_track = {"title": "Perfect", "artist": "Ed Sheeran"}
    library = [{"title": "Perfect", "artist": "", "filepath": "/music/perfect.mp3"}]
    results = match_tracks([playlist_track], library, threshold=60)
    assert results[0].status == "Found"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_matcher.py -v
```

Expected: `ModuleNotFoundError: No module named 'matcher'`

- [ ] **Step 3: Implement `matcher.py`**

```python
from dataclasses import dataclass
from rapidfuzz import fuzz


@dataclass
class MatchResult:
    playlist_title: str
    playlist_artist: str
    status: str          # "Found" or "Missing"
    matched_filepath: str


def build_comparison_string(artist: str, title: str) -> str:
    """Build the string used for fuzzy comparison."""
    if artist:
        return f"{artist} - {title}"
    return title


def match_tracks(
    playlist_tracks: list[dict],
    library_tracks: list[dict],
    threshold: int,
) -> list[MatchResult]:
    """Match each playlist track against the local library.

    Returns a MatchResult for every playlist track (duplicates preserved).
    """
    # Pre-compute comparison strings for the library once
    library_strings = [
        build_comparison_string(t["artist"], t["title"]) for t in library_tracks
    ]

    results = []
    for track in playlist_tracks:
        query = build_comparison_string(track["artist"], track["title"])
        best_score = -1
        best_filepath = ""

        for i, lib_string in enumerate(library_strings):
            score = fuzz.WRatio(query, lib_string)
            if score > best_score:
                best_score = score
                best_filepath = library_tracks[i]["filepath"]

        if best_score >= threshold:
            results.append(
                MatchResult(
                    playlist_title=track["title"],
                    playlist_artist=track["artist"],
                    status="Found",
                    matched_filepath=best_filepath,
                )
            )
        else:
            results.append(
                MatchResult(
                    playlist_title=track["title"],
                    playlist_artist=track["artist"],
                    status="Missing",
                    matched_filepath="",
                )
            )

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_matcher.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add matcher.py tests/test_matcher.py
git commit -m "feat: fuzzy matcher using WRatio"
```

---

### Task 9: Reporter

**Files:**
- Create: `reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_reporter.py
import csv
import os
from pathlib import Path
from matcher import MatchResult
from reporter import print_results, write_csv


def make_results():
    return [
        MatchResult("Perfect", "Ed Sheeran", "Found", "/music/perfect.mp3"),
        MatchResult("At Last", "Etta James", "Missing", ""),
    ]


def test_print_results_shows_found_section(capsys):
    print_results(make_results())
    out = capsys.readouterr().out
    assert "FOUND" in out.upper()
    assert "Perfect" in out
    assert "/music/perfect.mp3" in out


def test_print_results_shows_missing_section(capsys):
    print_results(make_results())
    out = capsys.readouterr().out
    assert "MISSING" in out.upper()
    assert "At Last" in out


def test_write_csv_creates_file(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    assert out_path.exists()


def test_write_csv_has_correct_columns(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    with open(out_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["playlist_track", "artist", "status", "matched_local_file"]


def test_write_csv_correct_rows(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["playlist_track"] == "Perfect"
    assert rows[0]["artist"] == "Ed Sheeran"
    assert rows[0]["status"] == "Found"
    assert rows[0]["matched_local_file"] == "/music/perfect.mp3"
    assert rows[1]["status"] == "Missing"
    assert rows[1]["matched_local_file"] == ""


def test_write_csv_overwrites_existing_file(tmp_path):
    out_path = tmp_path / "report.csv"
    out_path.write_text("old content")
    write_csv(make_results(), str(out_path))
    content = out_path.read_text()
    assert "old content" not in content
    assert "playlist_track" in content
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_reporter.py -v
```

Expected: `ModuleNotFoundError: No module named 'reporter'`

- [ ] **Step 3: Implement `reporter.py`**

```python
import csv
from matcher import MatchResult


def print_results(results: list[MatchResult]) -> None:
    found = [r for r in results if r.status == "Found"]
    missing = [r for r in results if r.status == "Missing"]

    print("\n=== FOUND ===")
    if found:
        for r in found:
            print(f"  {r.playlist_artist} - {r.playlist_title}")
            print(f"    -> {r.matched_filepath}")
    else:
        print("  (none)")

    print("\n=== MISSING ===")
    if missing:
        for r in missing:
            print(f"  {r.playlist_artist} - {r.playlist_title}")
    else:
        print("  (none)")

    print(f"\nSummary: {len(found)} found, {len(missing)} missing.\n")


def write_csv(results: list[MatchResult], output_path: str) -> None:
    fieldnames = ["playlist_track", "artist", "status", "matched_local_file"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "playlist_track": r.playlist_title,
                "artist": r.playlist_artist,
                "status": r.status,
                "matched_local_file": r.matched_filepath,
            })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_reporter.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add reporter.py tests/test_reporter.py
git commit -m "feat: reporter — terminal output and CSV export"
```

---

### Task 10: CLI Entry Point

**Files:**
- Create: `musicdedup.py`

No unit tests for the entry point — it is thin orchestration. Verified manually.

- [ ] **Step 1: Implement `musicdedup.py`**

```python
#!/usr/bin/env python3
"""musicdedup — compare a playlist against your local music library."""

import sys
import datetime
from config import load_config, ConfigError
from fetcher import detect_source, fetch_spotify, fetch_youtube_music, FetchError
from scanner import scan_library
from matcher import match_tracks
from reporter import print_results, write_csv


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python musicdedup.py <playlist_url>")
        sys.exit(1)

    url = sys.argv[1]

    # Load and validate config
    try:
        cfg = load_config()
    except ConfigError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Detect URL source
    try:
        source = detect_source(url)
    except FetchError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Fetch playlist
    print(f"Fetching playlist from {source.replace('_', ' ').title()}...")
    try:
        if source == "spotify":
            playlist = fetch_spotify(
                url,
                client_id=cfg["spotify_client_id"],
                client_secret=cfg["spotify_client_secret"],
            )
        else:
            playlist = fetch_youtube_music(url)
    except FetchError as e:
        print(f"Error: {e}")
        sys.exit(1)

    tracks = playlist["tracks"]
    if not tracks:
        print(f"Warning: playlist '{playlist['name']}' contains no tracks. Nothing to do.")
        sys.exit(0)

    print(f"Playlist: '{playlist['name']}' — {len(tracks)} tracks")

    # Scan local library
    print(f"Scanning library at: {cfg['library_path']} ...")
    library = scan_library(cfg["library_path"])
    print(f"Found {len(library)} local tracks.")

    # Match
    print("Matching...")
    results = match_tracks(tracks, library, threshold=cfg["threshold"])

    # Report
    print_results(results)

    today = datetime.date.today().strftime("%Y-%m-%d")
    csv_filename = f"{today}-{playlist['name']}.csv"
    write_csv(results, csv_filename)
    print(f"Results saved to: {csv_filename}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run a smoke test with a known good playlist URL**

```bash
python musicdedup.py https://open.spotify.com/playlist/<your_test_playlist_id>
```

Expected: terminal output with FOUND / MISSING sections and a CSV file created.

- [ ] **Step 3: Verify error cases work**

```bash
# Missing URL arg
python musicdedup.py
# Expected: "Usage: python musicdedup.py <playlist_url>"

# Invalid URL
python musicdedup.py https://soundcloud.com/artist/track
# Expected: "Error: Unrecognized playlist URL..."
```

- [ ] **Step 4: Commit**

```bash
git add musicdedup.py
git commit -m "feat: CLI entry point"
```

---

### Task 11: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# musicdedup

Compare a Spotify or YouTube Music playlist against your local music library.
Tells you which tracks you already have and which you need to download.

## Prerequisites

- Python 3.10 or higher
- A [Spotify Developer account](https://developer.spotify.com/dashboard) (only needed for Spotify playlists)

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd musicdedup
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure credentials

Copy the example config file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set:

```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
MUSIC_LIBRARY_PATH=/absolute/path/to/your/music/folder
MATCH_THRESHOLD=85
```

- `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are only required for Spotify playlist links.
  Get them from your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
- `MUSIC_LIBRARY_PATH` is the root folder of your local music collection.
- `MATCH_THRESHOLD` controls how strict matching is (0–100). Default is 85.
  Lower values match more loosely (catches more remixes); higher values require closer matches.

## Usage

```bash
python musicdedup.py <playlist_url>
```

### Examples

```bash
# Spotify playlist
python musicdedup.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"

# YouTube Music playlist
python musicdedup.py "https://music.youtube.com/playlist?list=PLxxxxx"
```

## Output

The tool prints results to the terminal:

```
=== FOUND ===
  Ed Sheeran - Perfect
    -> /music/Ed Sheeran - Perfect.mp3

=== MISSING ===
  Etta James - At Last

Summary: 1 found, 1 missing.

Results saved to: 2026-03-21-wedding-mix.csv
```

It also writes a CSV file to the current directory named `YYYY-MM-DD-<playlist-name>.csv`:

| playlist_track | artist | status | matched_local_file |
|---|---|---|---|
| Perfect | Ed Sheeran | Found | /music/Ed Sheeran - Perfect.mp3 |
| At Last | Etta James | Missing | |

If a CSV with the same name already exists, it is overwritten.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

### Task 12: Full Test Suite Check

- [ ] **Step 1: Run the complete test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS, no warnings about missing fixtures or imports.

- [ ] **Step 2: Commit if any fixes were needed**

```bash
git add config.py fetcher.py scanner.py matcher.py reporter.py musicdedup.py tests/
git commit -m "fix: address any issues from full test suite run"
```
