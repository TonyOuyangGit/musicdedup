import re
from dataclasses import dataclass, field
from rapidfuzz import fuzz, utils


_PARENS_RE = re.compile(r'\([^)]*\)')
_FEAT_RE = re.compile(r'\s+(?:ft\.?|feat\.?|featuring)\s+(?:(?! - ).)*', re.IGNORECASE)
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
class CandidateMatch:
    filepath: str
    score: float


@dataclass
class MatchResult:
    playlist_title: str
    playlist_artist: str
    status: str          # "Found" | "Missing" | "Candidate"
    matched_filepath: str
    match_score: float = 0.0
    candidates: list[CandidateMatch] = field(default_factory=list)


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

    Uses two-pass scoring (full string + annotation-stripped) and takes the max.
    Returns a MatchResult for every playlist track (duplicates preserved).
    """
    library_strings = [
        build_comparison_string(t["artist"], t["title"]) for t in library_tracks
    ]
    library_strings_stripped = [strip_annotations(s) for s in library_strings]

    results = []
    for track in playlist_tracks:
        query = build_comparison_string(track["artist"], track["title"])
        query_stripped = strip_annotations(query)

        scored = []
        for i, (lib_str, lib_stripped) in enumerate(
            zip(library_strings, library_strings_stripped)
        ):
            full_score = fuzz.token_sort_ratio(
                query, lib_str, processor=utils.default_process
            )
            stripped_score = fuzz.token_sort_ratio(
                query_stripped, lib_stripped, processor=utils.default_process
            )
            scored.append((max(full_score, stripped_score), library_tracks[i]["filepath"]))

        if not scored:
            results.append(
                MatchResult(
                    playlist_title=track["title"],
                    playlist_artist=track["artist"],
                    status="Missing",
                    matched_filepath="",
                )
            )
            continue

        best_score, best_filepath = max(scored, key=lambda x: x[0])

        if best_score >= threshold:
            results.append(
                MatchResult(
                    playlist_title=track["title"],
                    playlist_artist=track["artist"],
                    status="Found",
                    matched_filepath=best_filepath,
                    match_score=best_score,
                )
            )
        elif best_score >= threshold - CANDIDATE_MARGIN:
            in_zone = sorted(
                [(s, fp) for s, fp in scored if s >= threshold - CANDIDATE_MARGIN],
                key=lambda x: x[0],
                reverse=True,
            )[:2]
            candidates = [CandidateMatch(filepath=fp, score=s) for s, fp in in_zone]
            results.append(
                MatchResult(
                    playlist_title=track["title"],
                    playlist_artist=track["artist"],
                    status="Candidate",
                    matched_filepath="",
                    match_score=best_score,
                    candidates=candidates,
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
