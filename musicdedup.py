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
