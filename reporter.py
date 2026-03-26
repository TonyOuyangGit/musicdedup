import csv
from matcher import MatchResult


def print_results(results: list[MatchResult]) -> None:
    found = [r for r in results if r.status == "Found"]
    missing = [r for r in results if r.status == "Missing"]
    candidates = [r for r in results if r.status == "Candidate"]

    print("\n=== FOUND ===")
    if found:
        for r in found:
            print(f"  {r.playlist_artist} - {r.playlist_title}")
            print(f"    -> {r.matched_filepath}")
    else:
        print("  (none)")

    print("\n=== MISSING ===")
    if missing or candidates:
        for r in missing:
            print(f"  {r.playlist_artist} - {r.playlist_title}")
        for r in candidates:
            print(f"  {r.playlist_artist} - {r.playlist_title}")
            for c in r.candidates:
                name = c.filepath.split("/")[-1]
                print(f"    ~ possible: {name}  [{c.score:.0f}]")
    else:
        print("  (none)")

    print(
        f"\nSummary: {len(found)} found, {len(candidates)} candidate, {len(missing)} missing.\n"
    )


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
