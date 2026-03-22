import pytest
from matcher import build_comparison_string, match_tracks, MatchResult


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
    results = match_tracks([playlist_track], library, threshold=60)
    assert results[0].status == "Found"
