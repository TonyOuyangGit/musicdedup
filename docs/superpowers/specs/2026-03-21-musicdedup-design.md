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

**Minimum Python version:** 3.10

## Components

### 1. Playlist Fetcher

- **URL validation:** The tool inspects the URL domain to determine the source. If the URL does not match a recognized Spotify or YouTube Music playlist pattern, the tool exits immediately with a descriptive error message and a non-zero exit code. Non-playlist Spotify URLs (track, album, artist) are also rejected with a clear error.
- **Spotify:** Uses `spotipy` with the **Client Credentials flow** (`SpotifyClientCredentials`). Requires a Spotify Developer Client ID and Client Secret. Spotify credentials are validated **lazily** — only when a Spotify URL is provided. If `SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET` is missing and a Spotify URL is given, the tool exits with a descriptive error and a non-zero exit code. Private playlists are out of scope — if the API returns a 403 or 404, the tool exits with a descriptive error message and a non-zero exit code.
- **YouTube Music:** Uses `ytmusicapi`, which requires no authentication for public playlists. If the playlist is not found or inaccessible, the tool exits with a descriptive error and a non-zero exit code.
- **Empty playlist:** If the fetched playlist contains zero tracks, the tool prints a warning message and exits cleanly with exit code 0. No CSV is written.
- **Output:** A list of `{title, artist}` dicts for every track in the playlist. Duplicate entries are preserved — each playlist entry is processed independently and will appear as its own row in the output.
- **Playlist name sanitization:** The playlist name is fetched from the API response. Sanitization steps applied in order:
  1. Lowercase the name.
  2. Replace all non-alphanumeric characters (including spaces) with hyphens.
  3. Truncate the string resulting from step 2 to 50 characters.
  4. Strip any trailing hyphens from the truncated result.
  - If the playlist name is absent or empty after sanitization, the playlist ID is used as the fallback (IDs are already alphanumeric and require no further sanitization).

### 2. Library Scanner

- **Path validation:** If `MUSIC_LIBRARY_PATH` is not set in the environment or `.env` file, the tool exits immediately with the message `"Error: MUSIC_LIBRARY_PATH is not configured."` and a non-zero exit code — before any `os.path.abspath` call. If it is set, it is resolved to an absolute path using `os.path.abspath`. If the resolved path does not exist or is not an accessible directory, the tool exits with a descriptive error message and a non-zero exit code.
- Walks the configured local music folder recursively.
- Processes files with the following extensions: `.mp3`, `.flac`, `.m4a`, `.aiff`, `.wav`, `.ogg`.
- For each file, attempts to read embedded tags (`title`, `artist`) using `mutagen`. If `mutagen` raises any exception (corrupted file, unsupported variant, permissions error), the file is **skipped with a printed warning** and scanning continues.
- **Filename fallback:** If tags are absent or empty, parses the filename stem. Assumed format: `Artist - Title` (split on the first ` - ` with surrounding whitespace). If no such delimiter is present, the full stem is treated as the title and artist is left as an empty string.
- **Output:** An in-memory list of `{title, artist, filepath}` for every local track, where `filepath` is the absolute filesystem path resolved at scan time.

### 3. Fuzzy Matcher

- Uses `rapidfuzz` with the **`fuzz.WRatio` scorer**, which handles token reordering and is well-suited for catching remixes, alternate edits, and version variations.
- **Comparison string construction:** Each track (playlist or local) independently formats its own comparison string. If `artist` is non-empty, the string is `"artist - title"`. If `artist` is empty, the string is just `"title"`. The scorer compares one side's string against the other's — they may be in different formats if one side has an artist and the other does not.
- A configurable similarity threshold (default: 85, range: 0–100 integer) determines a match. If `MATCH_THRESHOLD` is not a valid integer in the range 0–100, the tool exits with a descriptive error and a non-zero exit code.
- Each playlist track is matched against all local tracks; the highest-scoring match above the threshold is used. In the case of a tie (two local tracks with equal top scores), the first match encountered in filesystem scan order is used.

### 4. Reporter

- **Terminal output:** Prints two clearly labelled sections:
  - **Found** — playlist title, artist, and the absolute path of the matched local file.
  - **Missing** — tracks with no local match (title and artist), ready for manual download.
- **CSV export:** Writes a file named `YYYY-MM-DD-<sanitized-playlist-name>.csv` (using the current run date) to the working directory. If a file with that name already exists, it is **overwritten silently**. Columns:
  - `playlist_track` — track title only (not combined with artist)
  - `artist` — artist from the playlist
  - `status` — `Found` or `Missing`
  - `matched_local_file` — absolute filesystem path of the matched local file; empty string if missing

## Configuration

All user-specific settings are provided via a `.env` file or shell environment variables. `python-dotenv` is loaded with `override=False`, meaning existing shell environment variables take precedence over values in the `.env` file. A `.env.example` file is included in the repository as a template.

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
MUSIC_LIBRARY_PATH=/path/to/your/music/folder
MATCH_THRESHOLD=85
```

- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` — required only for Spotify URLs; validated lazily.
- `MUSIC_LIBRARY_PATH` — required always; validated at startup before any other processing.
- `MATCH_THRESHOLD` — optional; defaults to 85 if not set. Must be an integer in range 0–100.

## Dependencies

| Package         | Purpose                              |
|-----------------|--------------------------------------|
| `spotipy`       | Spotify Web API client               |
| `ytmusicapi`    | YouTube Music playlist fetching      |
| `mutagen`       | Reading embedded ID3 tags            |
| `rapidfuzz`     | Fuzzy string matching                |
| `python-dotenv` | Loading `.env` configuration         |

## Documentation Requirements

The `README.md` must cover:

1. Prerequisites — Python 3.10+, Spotify Developer account (for Spotify URLs)
2. Creating and activating a virtual environment (`venv`)
3. Installing dependencies via `pip install -r requirements.txt`
4. Configuring credentials — copying `.env.example` and filling in values
5. Running the script with example commands
6. Understanding the output (terminal sections + CSV file)

## Error Handling Summary

| Condition | Behavior |
|---|---|
| `MUSIC_LIBRARY_PATH` not set | Exit with error, non-zero exit code |
| `MUSIC_LIBRARY_PATH` set but invalid path | Exit with error, non-zero exit code |
| `MATCH_THRESHOLD` not a valid integer 0–100 | Exit with error, non-zero exit code |
| Unrecognized URL (not Spotify/YTMusic playlist) | Exit with error, non-zero exit code |
| Non-playlist Spotify URL (track, album, artist) | Exit with error, non-zero exit code |
| Spotify credentials missing when Spotify URL given | Exit with error, non-zero exit code |
| Playlist not found or private (403/404) | Exit with error, non-zero exit code |
| Playlist is empty (zero tracks) | Print warning, exit cleanly (exit code 0), no CSV written |
| `mutagen` exception on a single file | Print warning, skip file, continue scanning |
| CSV output file already exists | Overwrite silently |

## Out of Scope

- Automatic downloading of missing tracks
- Text-list input (non-URL playlists)
- Private Spotify playlists
- A GUI or web interface
- Playlist management or editing
