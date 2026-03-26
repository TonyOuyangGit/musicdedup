import re
from dataclasses import dataclass, field
from rapidfuzz import fuzz, utils


_PARENS_RE = re.compile(r'\([^)]*\)')
_FEAT_RE = re.compile(r'\s+(?:ft\.?|feat\.?|featuring)\s+.*', re.IGNORECASE)
_WHITESPACE_RE = re.compile(r'\s{2,}')


CANDIDATE_MARGIN = 15


def strip_annotations(s: str) -> str:
    """Remove version annotations and featuring clauses for relaxed comparison.

    Steps (in order):
    1. Remove all parenthesised content — (Radio Edit), (feat. X), etc.
    2. Remove bare featuring clauses — ft X, feat. X, featuring X.
    3. Collapse runs of whitespace and strip edges.
    """
    s = _PARENS_RE.sub('', s)
    s = _FEAT_RE.sub('', s)
    s = _WHITESPACE_RE.sub(' ', s)
    return s.strip()


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
            score = fuzz.token_sort_ratio(query, lib_string, processor=utils.default_process)
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
