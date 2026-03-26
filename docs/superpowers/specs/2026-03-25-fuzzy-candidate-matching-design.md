# Fuzzy Candidate Matching Enhancement

**Date:** 2026-03-25
**Status:** Approved

## Problem

The current matcher uses `token_sort_ratio` on raw comparison strings. This misses genuine same-song variants where the local file differs from the playlist track by:
- Version annotations in parentheses — `(Radio Edit)`, `(Clean)`, `(Quick Hit Dirty)`, `(Intro)`, etc.
- Featured-artist clauses — `ft Foxes`, `feat. T-Pain`, `featuring X`
- Artist/title ordering differences — `Clarity (Radio Edit) - Zedd ft Foxes` vs `Zedd - Clarity`

These tracks score below the 85-point threshold and appear as Missing even though they are clearly the same song.

Additionally, truly ambiguous near-misses (scoring just below the threshold) are silently discarded with no way for the user to review them.

## Goals

1. Pull genuine same-song variants above the confidence threshold so they appear as Found.
2. Surface near-miss tracks as Candidates (instead of Missing) so the user can review them.

## Non-Goals

- Automatic resolution of candidates — the user decides manually.
- Changing the default threshold value.

---

## Design

### 1. Matching Algorithm — Two-Pass Scoring

For every (playlist track, library track) pair, compute **two scores** and take the maximum:

- **Full score** — `token_sort_ratio` on the original comparison strings (existing behaviour).
- **Stripped score** — `token_sort_ratio` on annotation-stripped versions of both strings.

The best score across both passes determines the final result.

#### Strip Function

The `strip_annotations(s)` function:
1. Removes all parenthesised content: `\([^)]*\)` → `""`
2. Removes bare featuring clauses: `\s+(?:ft\.?|feat\.?|featuring)\s+.*` → `""` (case-insensitive)

Examples:
```
"Clarity (Radio Edit) - Zedd ft Foxes"      → "Clarity - Zedd"
"Zedd - Clarity"                            → "Zedd - Clarity"

"Low (Quick Hit Dirty) - Flo Rida ft T-pain" → "Low - Flo Rida"
"Flo Rida - Low (feat. T-Pain)"              → "Flo Rida - Low"
```

Both are then passed through `utils.default_process` (lowercase, strip non-alphanumeric) and `token_sort_ratio` is applied. The stripped pairs above score 100.

### 2. Data Model

Two changes to `matcher.py`:

```python
@dataclass
class CandidateMatch:
    filepath: str
    score: float

@dataclass
class MatchResult:
    playlist_title: str
    playlist_artist: str
    status: str                        # "Found" | "Missing" | "Candidate"
    matched_filepath: str
    match_score: float                 # score of winning match (0.0 for Missing)
    candidates: list[CandidateMatch]   # non-empty only when status="Candidate"
```

`candidates` uses `field(default_factory=list)` so existing call sites that only supply the first four fields continue to work.

### 3. Result Classification

```
best_score >= threshold          → Found
threshold - 15 <= best_score < threshold  → Candidate (up to top-2 by score)
best_score < threshold - 15      → Missing
```

The candidate window (`15`) is a module-level constant `CANDIDATE_MARGIN = 15` so it can be adjusted without touching the logic.

Pre-computation: both `library_strings` (full) and `library_strings_stripped` (stripped) are built once before the inner loop, keeping the O(P×L) complexity unchanged.

### 4. Terminal Output

Candidates are folded into the `=== MISSING ===` section:

```
=== MISSING ===
  Taylor Swift - Shake It Off
  Flo Rida - Low (feat. T-Pain)
    ~ possible: Low (Quick Hit Dirty) - Flo Rida ft T-pain.mp3  [72]
    ~ possible: Flo Rida - Low.mp3  [61]

Summary: 3 found, 1 candidate, 1 missing.
```

Candidate lines are indented 4 spaces and prefixed with `~`.

### 5. CSV Output

A `match_score` column is added. Candidate tracks emit **one row per candidate**:

```
playlist_track,artist,status,matched_local_file,match_score
Low (feat. T-Pain),Flo Rida,Candidate,Low (Quick Hit Dirty)...mp3,72.0
Low (feat. T-Pain),Flo Rida,Candidate,Flo Rida - Low.mp3,61.0
```

Found rows include `match_score`. Missing rows leave it blank.

---

## Files Affected

| File | Change |
|------|--------|
| `matcher.py` | Add `strip_annotations`, `CandidateMatch`, update `MatchResult`, rewrite `match_tracks` |
| `reporter.py` | Update `print_results` (candidate display), update `write_csv` (score column, candidate rows) |
| `tests/test_matcher.py` | Update existing tests for new fields; add stripped-match and candidate tests |
| `tests/test_reporter.py` | Update for new CSV schema and candidate terminal output |

## Testing

Key new test cases:
- `strip_annotations` unit tests (parens removed, feat clauses removed, clean strings unchanged)
- Stripped match: `"Zedd - Clarity"` matches `"Clarity (Radio Edit) - Zedd ft Foxes"` as Found
- Stripped match: `"Flo Rida - Low (feat. T-Pain)"` matches `"Low (Quick Hit Dirty) - Flo Rida ft T-pain"` as Found
- Candidate zone: track scoring in `[threshold-15, threshold)` returns `status="Candidate"` with up to 2 entries
- Below floor: track scoring below `threshold-15` returns `status="Missing"` with empty candidates
- CSV: candidate rows written correctly with score column
