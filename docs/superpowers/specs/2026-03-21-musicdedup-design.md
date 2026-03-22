# musicdedup — Design Spec

**Date:** 2026-03-21
**Status:** Approved

## Overview

A Python CLI tool for wedding DJs to compare a Spotify or YouTube Music playlist against a local music library. The tool identifies which tracks already exist locally and which need to be downloaded.

## Usage

```bash
python musicdedup.py <playlist_url>
```

The URL can be a Spotify share link (`open.spotify.com/playlist/...`) or a YouTube Music share link (`music.youtube.com/playlist/...`). The tool auto-detects the source.

## Components

### 1. Playlist Fetcher

- **Spotify:** Uses `spotipy` with the Spotify Web API. Requires a free Spotify Developer account with a Client ID and Client Secret.
- **YouTube Music:** Uses `ytmusicapi`, which requires no authentication for public playlists.
- **Output:** A list of `{title, artist}` dicts for every track in the playlist.

### 2. Library Scanner

- Walks a configured local music folder (set via env var or config).
- For each music file, attempts to read embedded ID3 tags (`title`, `artist`) using `mutagen`.
- Falls back to parsing the filename if tags are absent or empty.
- **Output:** An in-memory list of `{title, artist, filepath}` for every local track.

### 3. Fuzzy Matcher

- Uses `rapidfuzz` to compare each playlist track against every local track.
- Matching is performed on the combined `"artist - title"` string.
- A configurable similarity threshold (default: 85%) determines a match.
- The threshold catches remixes, edits, and alternate versions while minimising false positives.
- Each playlist track is matched against all local tracks; the highest-scoring match above the threshold is used.

### 4. Reporter

- **Terminal output:** Prints two clearly labelled sections:
  - **Found** — playlist track and the matched local file path.
  - **Missing** — tracks with no local match, ready for manual download.
- **CSV export:** Writes a file named `YYYY-MM-DD-<playlist-name>.csv` to the working directory with columns:
  - `playlist_track` — title from the playlist
  - `artist` — artist from the playlist
  - `status` — `Found` or `Missing`
  - `matched_local_file` — local filepath if found, empty if missing

## Configuration

All user-specific settings are provided via a `.env` file (not committed to version control):

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
MUSIC_LIBRARY_PATH=/path/to/your/music/folder
MATCH_THRESHOLD=85
```

## Dependencies

| Package       | Purpose                              |
|---------------|--------------------------------------|
| `spotipy`     | Spotify Web API client               |
| `ytmusicapi`  | YouTube Music playlist fetching      |
| `mutagen`     | Reading embedded ID3 tags            |
| `rapidfuzz`   | Fuzzy string matching                |
| `python-dotenv` | Loading `.env` configuration       |

## Documentation Requirements

The `README.md` must cover:

1. Prerequisites — Python 3.x, Spotify Developer account
2. Creating and activating a virtual environment (`venv`)
3. Installing dependencies via `pip install -r requirements.txt`
4. Configuring credentials — copying `.env.example` and filling in values
5. Running the script with example commands
6. Understanding the output (terminal sections + CSV file)

## Out of Scope

- Automatic downloading of missing tracks
- Text-list input (non-URL playlists)
- A GUI or web interface
- Playlist management or editing
