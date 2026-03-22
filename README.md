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
