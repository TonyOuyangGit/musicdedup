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
