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

`strip_annotations(s: str) -> str` applies three steps **in this order**:

1. Remove all parenthesised content: `\([^)]*\)` → `""`. Parens are removed first because `(feat. X)` is the most common encoding; removing the whole group is cleaner than trying to match feat inside parens with the feat regex.
2. Remove bare featuring clauses: `\s+(?:ft\.?|feat\.?|featuring)\s+.*` → `""` (case-insensitive). This catches `ft Foxes`, `feat. T-Pain`, etc. that appear outside parens.
3. Collapse internal whitespace runs to a single space and strip leading/trailing whitespace. This step is performed **inside `strip_annotations`** so callers receive a clean string. `utils.default_process` is applied afterwards (lowercase, remove non-alphanumeric), but the whitespace is already normalised before it is called.

**Known limitation:** content that follows a `(feat. X)` group and is not itself in parens (e.g. `"Song (feat. Artist) Remix Version"`) will leave `"Remix Version"` in the stripped string. In practice this is rare since version words appear before or inside the feat clause. No test currently covers this pattern.

Examples (after `strip_annotations`, before `default_process`):
```
"Clarity (Radio Edit) - Zedd ft Foxes"      → "Clarity - Zedd"
"Zedd - Clarity"                            → "Zedd - Clarity"
→ token_sort_ratio("clarity zedd", "clarity zedd") = 100 ✓

"Low (Quick Hit Dirty) - Flo Rida ft T-pain" → "Low - Flo Rida"
"Flo Rida - Low (feat. T-Pain)"              → "Flo Rida - Low"
→ token_sort_ratio("flo low rida", "flo low rida") = 100 ✓
```

Note: the intermediate stripped string may contain a double space where a parenthesised group was removed (e.g. `"Clarity  - Zedd"`). Step 3 (whitespace collapse) or `utils.default_process` removes it before comparison.

Pre-computation: both `library_strings` (full) and `library_strings_stripped` (stripped) are built once before the inner loop to keep O(P×L) complexity unchanged.

### 2. Data Model

```python
@dataclass
class CandidateMatch:
    filepath: str
    score: float

@dataclass
class MatchResult:
    playlist_title: str
    playlist_artist: str
    status: str                             # "Found" | "Missing" | "Candidate"
    matched_filepath: str
    match_score: float = 0.0               # default 0.0 — preserves 4-arg construction
    candidates: list[CandidateMatch] = field(default_factory=list)
```

`match_score` has a default of `0.0` so all existing 4-argument positional constructions (e.g. in tests) continue to work without modification.

`matched_filepath` values by status:
- `"Found"` — path of the winning library file.
- `"Missing"` — empty string `""`.
- `"Candidate"` — empty string `""`. Candidate file paths live exclusively in `candidates`.

### 3. Result Classification

```
best_score >= threshold                      → Found
threshold - CANDIDATE_MARGIN <= best_score < threshold  → Candidate (top-2 by score)
best_score < threshold - CANDIDATE_MARGIN    → Missing
```

`CANDIDATE_MARGIN = 15` is a module-level constant. At the default threshold of 85, candidates span scores 70–84.

### 4. Terminal Output

Candidates are folded into the `=== MISSING ===` section with a `~` prefix and 4-space indent:

```
=== MISSING ===
  Taylor Swift - Shake It Off
  Flo Rida - Low (feat. T-Pain)
    ~ possible: Low (Quick Hit Dirty) - Flo Rida ft T-pain.mp3  [72]
    ~ possible: Flo Rida - Low.mp3  [61]

Summary: 3 found, 1 candidate, 1 missing.
```

The three summary counts are **mutually exclusive**: a Candidate is counted once as "candidate", not as "missing". The missing count reflects only `status == "Missing"` results.

### 5. CSV Output

A `match_score` column is appended. Candidate tracks emit **one row per candidate file**; both rows share the same `playlist_track`/`artist`. The `matched_local_file` column for Candidate rows is populated from `CandidateMatch.filepath` (not from `MatchResult.matched_filepath`, which is `""`).

```
playlist_track,artist,status,matched_local_file,match_score
Perfect,Ed Sheeran,Found,/music/perfect.mp3,100.0
Shake It Off,Taylor Swift,Missing,,
Low (feat. T-Pain),Flo Rida,Candidate,Low (Quick Hit Dirty)...mp3,72.0
Low (feat. T-Pain),Flo Rida,Candidate,Flo Rida - Low.mp3,61.0
```

Found rows include `match_score`. Missing rows leave both `matched_local_file` and `match_score` blank.

---

## Files Affected

| File | Change |
|------|--------|
| `matcher.py` | Add `strip_annotations`, `CandidateMatch`, `CANDIDATE_MARGIN`; update `MatchResult`; rewrite `match_tracks` |
| `reporter.py` | Update `print_results` (candidate display + summary); update `write_csv` (score column, candidate rows) |
| `tests/test_matcher.py` | Add stripped-match and candidate tests; update any tests that inspect `MatchResult` fields added |
| `tests/test_reporter.py` | Update for new CSV schema and candidate terminal output |

## Testing

Key new test cases for `matcher.py`:
- `strip_annotations` unit tests: parens removed, bare feat clauses removed, clean strings unchanged, whitespace collapsed
- Stripped match: `"Zedd - Clarity"` matches `"Clarity (Radio Edit) - Zedd ft Foxes"` as Found at threshold 85
- Stripped match: `"Flo Rida - Low (feat. T-Pain)"` matches `"Low (Quick Hit Dirty) - Flo Rida ft T-pain"` as Found at threshold 85
- Candidate zone: track scoring in `[threshold-15, threshold)` returns `status="Candidate"` with up to 2 entries sorted by score descending
- Candidate cap: when 3+ library tracks fall in the candidate zone, only the top 2 are returned
- Below floor: track scoring below `threshold-15` returns `status="Missing"` with empty candidates list

Key new test cases for `reporter.py`:
- CSV `match_score` column present and populated for Found; blank for Missing
- Candidate rows: one CSV row per candidate with correct filepath and score
- Terminal: candidate lines appear under the correct Missing entry with `~` prefix
- Summary line counts candidates separately from missing
