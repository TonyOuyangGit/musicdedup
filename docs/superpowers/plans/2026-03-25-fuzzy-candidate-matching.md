# Fuzzy Candidate Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve fuzzy matching to surface version-annotated local files as Found matches, and show near-misses as Candidates instead of silently dropping them.

**Architecture:** Two-pass scoring in `match_tracks` — full string score + annotation-stripped score, take the max. Scores ≥ threshold → Found; scores in `[threshold−15, threshold)` → Candidate with up to 2 filepath suggestions; below floor → Missing. Reporter folds Candidates into the MISSING section with `~` prefix lines and writes one CSV row per candidate.

**Tech Stack:** Python 3.9+, rapidfuzz (`fuzz.token_sort_ratio`, `utils.default_process`), pytest, csv stdlib

---

## File Map

| File | What Changes |
|------|-------------|
| `matcher.py` | Add `CANDIDATE_MARGIN`, `strip_annotations`, `CandidateMatch`; update `MatchResult`; rewrite `match_tracks` |
| `reporter.py` | Update `print_results` (candidate lines + 3-count summary); update `write_csv` (add `match_score` column, one row per candidate) |
| `tests/test_matcher.py` | Add `strip_annotations` unit tests, two stripped-match integration tests, candidate zone / cap / floor tests |
| `tests/test_reporter.py` | Update column-check test; add candidate terminal and CSV tests |

---

## Task 1: `strip_annotations` — tests then implementation

**Files:**
- Modify: `matcher.py`
- Modify: `tests/test_matcher.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_matcher.py` (after existing imports, add `from matcher import strip_annotations`):

```python
from matcher import build_comparison_string, match_tracks, MatchResult, strip_annotations


def test_strip_removes_parens():
    assert strip_annotations("Clarity (Radio Edit)") == "Clarity"


def test_strip_removes_feat_in_parens():
    assert strip_annotations("Low (feat. T-Pain)") == "Low"


def test_strip_removes_bare_ft():
    assert strip_annotations("Clarity - Zedd ft Foxes") == "Clarity - Zedd"


def test_strip_removes_bare_feat_dot():
    assert strip_annotations("Song feat. Artist") == "Song"


def test_strip_removes_bare_featuring():
    assert strip_annotations("Song featuring Artist Name") == "Song"


def test_strip_clean_string_unchanged():
    assert strip_annotations("Zedd - Clarity") == "Zedd - Clarity"


def test_strip_collapses_whitespace_after_parens():
    # Removing "(Radio Edit)" leaves double space; must collapse to single
    assert strip_annotations("Clarity (Radio Edit) - Zedd") == "Clarity - Zedd"


def test_strip_multiple_parens():
    assert strip_annotations("Song (Intro Clean) (Dirty)") == "Song"
```

- [ ] **Step 2: Run tests to confirm they all fail**

```bash
cd /Users/tony/workspaces/musicdedup && source venv/bin/activate
pytest tests/test_matcher.py::test_strip_removes_parens tests/test_matcher.py::test_strip_clean_string_unchanged -v
```

Expected: `ImportError: cannot import name 'strip_annotations'`

- [ ] **Step 3: Implement `strip_annotations` in `matcher.py`**

Add at the top of `matcher.py`, after the existing imports:

```python
import re
from dataclasses import dataclass, field

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
```

The existing `from dataclasses import dataclass` import must be changed to `from dataclasses import dataclass, field` (needed for Task 2).

- [ ] **Step 4: Run all strip tests**

```bash
pytest tests/test_matcher.py -k "test_strip" -v
```

Expected: all 8 pass.

- [ ] **Step 5: Commit**

```bash
git add matcher.py tests/test_matcher.py
git commit -m "feat: add strip_annotations for version-annotation removal"
```

---

## Task 2: Updated data model — `CandidateMatch` and `MatchResult`

**Files:**
- Modify: `matcher.py`
- Test: run existing suite to verify no regressions

- [ ] **Step 1: Update the dataclasses in `matcher.py`**

Replace the existing `MatchResult` dataclass (and add `CandidateMatch` before it):

```python
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
```

`match_score` defaults to `0.0` so all existing 4-argument constructions in tests continue to work unchanged.

- [ ] **Step 2: Verify existing tests still pass**

```bash
pytest tests/test_matcher.py tests/test_reporter.py -v
```

Expected: all existing tests pass (no test changes required — the new fields have defaults).

- [ ] **Step 3: Commit**

```bash
git add matcher.py
git commit -m "feat: add CandidateMatch dataclass and extend MatchResult with match_score/candidates"
```

---

## Task 3: Two-pass matching in `match_tracks`

**Files:**
- Modify: `matcher.py`
- Modify: `tests/test_matcher.py`

- [ ] **Step 1: Write the failing integration tests**

Add to `tests/test_matcher.py`:

```python
# --- Two-pass stripped matching ---

def test_stripped_match_radio_edit():
    """Playlist has bare title; library has (Radio Edit) + featured artist."""
    playlist = [{"artist": "Zedd", "title": "Clarity"}]
    library = [
        {
            "artist": "Zedd ft Foxes",
            "title": "Clarity (Radio Edit)",
            "filepath": "/music/clarity.mp3",
        }
    ]
    results = match_tracks(playlist, library, threshold=85)
    assert results[0].status == "Found"
    assert results[0].matched_filepath == "/music/clarity.mp3"


def test_stripped_match_quick_hit():
    """Playlist has feat.; library has (Quick Hit Dirty) variant with reordered artist."""
    playlist = [{"artist": "Flo Rida", "title": "Low (feat. T-Pain)"}]
    library = [
        {
            "artist": "Flo Rida ft T-pain",
            "title": "Low (Quick Hit Dirty)",
            "filepath": "/music/low.mp3",
        }
    ]
    results = match_tracks(playlist, library, threshold=85)
    assert results[0].status == "Found"
    assert results[0].matched_filepath == "/music/low.mp3"


# --- Candidate zone ---

def test_candidate_zone_returns_candidate_status():
    """Score in [threshold-15, threshold) → Candidate with filepath in candidates list."""
    playlist = [{"artist": "Taylor Swift", "title": "Love Story"}]
    library = [
        # "Taylor Swift - Love Story 2021" strips to same, scores ~90 vs "Taylor Swift - Love Story"
        # At threshold=100, 90 falls in [85, 100) → Candidate
        {
            "artist": "Taylor Swift",
            "title": "Love Story 2021",
            "filepath": "/music/love_story_2021.mp3",
        }
    ]
    results = match_tracks(playlist, library, threshold=100)
    assert results[0].status == "Candidate"
    assert len(results[0].candidates) == 1
    assert results[0].candidates[0].filepath == "/music/love_story_2021.mp3"
    assert results[0].matched_filepath == ""


def test_candidate_capped_at_two():
    """When 3+ library tracks fall in the zone, only the top 2 are returned."""
    playlist = [{"artist": "Taylor Swift", "title": "Love Story"}]
    library = [
        {"artist": "Taylor Swift", "title": "Love Story 2021", "filepath": "/a.mp3"},
        {"artist": "Taylor Swift", "title": "Love Story Live", "filepath": "/b.mp3"},
        {"artist": "Taylor Swift", "title": "Love Story Acoustic", "filepath": "/c.mp3"},
    ]
    results = match_tracks(playlist, library, threshold=100)
    assert results[0].status == "Candidate"
    assert len(results[0].candidates) <= 2


def test_candidates_ordered_by_score_descending():
    """First candidate has higher or equal score than second."""
    playlist = [{"artist": "Taylor Swift", "title": "Love Story"}]
    library = [
        {"artist": "Taylor Swift", "title": "Love Story 2021", "filepath": "/a.mp3"},
        {"artist": "Taylor Swift", "title": "Love Story Live Version Extended", "filepath": "/b.mp3"},
    ]
    results = match_tracks(playlist, library, threshold=100)
    if results[0].status == "Candidate" and len(results[0].candidates) == 2:
        assert results[0].candidates[0].score >= results[0].candidates[1].score


def test_below_candidate_floor_is_missing():
    """Score below threshold-15 → Missing with empty candidates."""
    playlist = [{"artist": "Queen", "title": "Bohemian Rhapsody"}]
    library = [
        {"artist": "Ed Sheeran", "title": "Perfect", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks(playlist, library, threshold=85)
    assert results[0].status == "Missing"
    assert results[0].candidates == []


def test_found_result_includes_match_score():
    """Found results carry the winning match score."""
    playlist = [{"artist": "Ed Sheeran", "title": "Perfect"}]
    library = [
        {"artist": "Ed Sheeran", "title": "Perfect", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks(playlist, library, threshold=85)
    assert results[0].status == "Found"
    assert results[0].match_score == 100.0
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
pytest tests/test_matcher.py -k "stripped_match or candidate or below_candidate or found_result_includes" -v
```

Expected: all fail (the current `match_tracks` has no stripped pass and doesn't populate `match_score` or `candidates`).

- [ ] **Step 3: Rewrite `match_tracks` in `matcher.py`**

Replace the entire `match_tracks` function:

```python
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
```

- [ ] **Step 4: Run the full matcher test suite**

```bash
pytest tests/test_matcher.py -v
```

Expected: all tests pass.

> **Note on score-based tests:** `test_candidate_zone_returns_candidate_status` and `test_candidate_capped_at_two` rely on `token_sort_ratio` scoring "Love Story 2021" in the range `[85, 100)` at `threshold=100`. If a test fails with `status == "Found"` instead of `"Candidate"`, lower the threshold by 5 until the test passes. If it fails with `status == "Missing"`, the score is below 85 — try replacing `"Love Story 2021"` with `"Love Story Album"` (shorter suffix, higher score).

- [ ] **Step 5: Commit**

```bash
git add matcher.py tests/test_matcher.py
git commit -m "feat: two-pass scoring in match_tracks — strips annotations for relaxed matching, surfaces candidates"
```

---

## Task 4: Update terminal reporter

**Files:**
- Modify: `reporter.py`
- Modify: `tests/test_reporter.py`

- [ ] **Step 1: Write the failing reporter tests**

Add to `tests/test_reporter.py`:

```python
from matcher import MatchResult, CandidateMatch


def make_candidate_result():
    return MatchResult(
        playlist_title="Low (feat. T-Pain)",
        playlist_artist="Flo Rida",
        status="Candidate",
        matched_filepath="",
        match_score=72.0,
        candidates=[
            CandidateMatch(filepath="/music/Low (Quick Hit Dirty).mp3", score=72.0),
            CandidateMatch(filepath="/music/Flo Rida - Low.mp3", score=61.0),
        ],
    )


def test_print_results_shows_candidate_under_missing(capsys):
    results = make_results() + [make_candidate_result()]
    print_results(results)
    out = capsys.readouterr().out
    # Candidate appears in MISSING section
    assert "Low (feat. T-Pain)" in out
    # Candidate lines use ~ prefix
    assert "~ possible:" in out
    assert "Low (Quick Hit Dirty)" in out


def test_print_results_summary_counts_candidate_separately(capsys):
    results = make_results() + [make_candidate_result()]
    print_results(results)
    out = capsys.readouterr().out
    # Summary: 1 found, 1 candidate, 1 missing (make_results has 1 Found + 1 Missing)
    assert "1 candidate" in out
    assert "1 missing" in out


def test_print_results_candidate_shows_score(capsys):
    print_results([make_candidate_result()])
    out = capsys.readouterr().out
    assert "[72]" in out
    assert "[61]" in out
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_reporter.py -k "candidate" -v
```

Expected: fail — current `print_results` has no candidate handling.

- [ ] **Step 3: Rewrite `print_results` in `reporter.py`**

Replace the entire `print_results` function:

```python
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
```

- [ ] **Step 4: Run all reporter tests**

```bash
pytest tests/test_reporter.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add reporter.py tests/test_reporter.py
git commit -m "feat: reporter shows candidates under MISSING with ~ prefix and 3-count summary"
```

---

## Task 5: Update CSV output

**Files:**
- Modify: `reporter.py`
- Modify: `tests/test_reporter.py`

- [ ] **Step 1: Update the failing column test and add new CSV tests**

In `tests/test_reporter.py`, update `test_write_csv_has_correct_columns` and add new tests:

```python
def test_write_csv_has_correct_columns(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    with open(out_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == [
            "playlist_track", "artist", "status", "matched_local_file", "match_score"
        ]


def test_write_csv_found_row_includes_score(tmp_path):
    out_path = tmp_path / "report.csv"
    result = MatchResult("Perfect", "Ed Sheeran", "Found", "/music/perfect.mp3", match_score=100.0)
    write_csv([result], str(out_path))
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["match_score"] == "100.0"


def test_write_csv_missing_row_has_blank_score(tmp_path):
    out_path = tmp_path / "report.csv"
    result = MatchResult("Song", "Artist", "Missing", "")
    write_csv([result], str(out_path))
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["match_score"] == ""
    assert rows[0]["matched_local_file"] == ""


def test_write_csv_candidate_emits_one_row_per_candidate(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv([make_candidate_result()], str(out_path))
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["status"] == "Candidate"
    assert rows[0]["matched_local_file"] == "/music/Low (Quick Hit Dirty).mp3"
    assert rows[0]["match_score"] == "72.0"
    assert rows[1]["matched_local_file"] == "/music/Flo Rida - Low.mp3"
    assert rows[1]["match_score"] == "61.0"


def test_write_csv_candidate_rows_share_playlist_track(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv([make_candidate_result()], str(out_path))
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["playlist_track"] == rows[1]["playlist_track"] == "Low (feat. T-Pain)"
    assert rows[0]["artist"] == rows[1]["artist"] == "Flo Rida"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_reporter.py -k "score or candidate_emits or candidate_rows" -v
```

Expected: `test_write_csv_has_correct_columns` fails (missing `match_score` column); new tests fail (function unchanged).

- [ ] **Step 3: Rewrite `write_csv` in `reporter.py`**

Replace the entire `write_csv` function:

```python
def write_csv(results: list[MatchResult], output_path: str) -> None:
    fieldnames = [
        "playlist_track", "artist", "status", "matched_local_file", "match_score"
    ]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            if r.status == "Candidate":
                for c in r.candidates:
                    writer.writerow({
                        "playlist_track": r.playlist_title,
                        "artist": r.playlist_artist,
                        "status": "Candidate",
                        "matched_local_file": c.filepath,
                        "match_score": c.score,
                    })
            else:
                writer.writerow({
                    "playlist_track": r.playlist_title,
                    "artist": r.playlist_artist,
                    "status": r.status,
                    "matched_local_file": r.matched_filepath,
                    "match_score": r.match_score if r.status == "Found" else "",
                })
```

- [ ] **Step 4: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add reporter.py tests/test_reporter.py
git commit -m "feat: CSV adds match_score column, candidate tracks emit one row per candidate"
```

---

## Final Smoke Test

After all tasks are complete, run a quick end-to-end sanity check against the real test library:

```bash
cd /Users/tony/workspaces/musicdedup && source venv/bin/activate
python musicdedup.py <your-playlist-url>
```

Verify:
- Zedd - Clarity appears as Found (matched to the `(Radio Edit)` file)
- Any near-misses appear in `=== MISSING ===` with `~ possible:` lines
- The summary line shows three separate counts
- The CSV contains a `match_score` column and one row per candidate
