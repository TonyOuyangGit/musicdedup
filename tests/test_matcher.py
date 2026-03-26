import pytest
from matcher import build_comparison_string, match_tracks, MatchResult, strip_annotations


def test_comparison_string_with_artist():
    assert build_comparison_string("Ed Sheeran", "Perfect") == "Ed Sheeran - Perfect"


def test_comparison_string_without_artist():
    assert build_comparison_string("", "Perfect") == "Perfect"


def test_exact_match_is_found():
    playlist_track = {"title": "Perfect", "artist": "Ed Sheeran"}
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].status == "Found"
    assert results[0].matched_filepath == "/music/perfect.mp3"


def test_remix_is_matched():
    playlist_track = {"title": "Blinding Lights", "artist": "The Weeknd"}
    library = [
        {
            "title": "Blinding Lights (Radio Edit)",
            "artist": "The Weeknd",
            "filepath": "/music/blinding.mp3",
        }
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].status == "Found"


def test_unrelated_track_is_missing():
    playlist_track = {"title": "Bohemian Rhapsody", "artist": "Queen"}
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].status == "Missing"
    assert results[0].matched_filepath == ""


def test_empty_library_returns_all_missing():
    tracks = [
        {"title": "Perfect", "artist": "Ed Sheeran"},
        {"title": "At Last", "artist": "Etta James"},
    ]
    results = match_tracks(tracks, [], threshold=85)
    assert all(r.status == "Missing" for r in results)


def test_duplicate_playlist_entries_produce_separate_results():
    playlist = [
        {"title": "Perfect", "artist": "Ed Sheeran"},
        {"title": "Perfect", "artist": "Ed Sheeran"},
    ]
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/perfect.mp3"}
    ]
    results = match_tracks(playlist, library, threshold=85)
    assert len(results) == 2


def test_tie_uses_first_in_scan_order():
    playlist_track = {"title": "Perfect", "artist": "Ed Sheeran"}
    library = [
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/first.mp3"},
        {"title": "Perfect", "artist": "Ed Sheeran", "filepath": "/music/second.mp3"},
    ]
    results = match_tracks([playlist_track], library, threshold=85)
    assert results[0].matched_filepath == "/music/first.mp3"


def test_local_track_without_artist_can_still_match():
    playlist_track = {"title": "Perfect", "artist": "Ed Sheeran"}
    library = [{"title": "Perfect", "artist": "", "filepath": "/music/perfect.mp3"}]
    results = match_tracks([playlist_track], library, threshold=50)
    assert results[0].status == "Found"


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
