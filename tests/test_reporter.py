import csv
import os
from pathlib import Path
from matcher import MatchResult
from reporter import print_results, write_csv


def make_results():
    return [
        MatchResult("Perfect", "Ed Sheeran", "Found", "/music/perfect.mp3"),
        MatchResult("At Last", "Etta James", "Missing", ""),
    ]


def test_print_results_shows_found_section(capsys):
    print_results(make_results())
    out = capsys.readouterr().out
    assert "FOUND" in out.upper()
    assert "Perfect" in out
    assert "/music/perfect.mp3" in out


def test_print_results_shows_missing_section(capsys):
    print_results(make_results())
    out = capsys.readouterr().out
    assert "MISSING" in out.upper()
    assert "At Last" in out


def test_write_csv_creates_file(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    assert out_path.exists()


def test_write_csv_has_correct_columns(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    with open(out_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["playlist_track", "artist", "status", "matched_local_file"]


def test_write_csv_correct_rows(tmp_path):
    out_path = tmp_path / "report.csv"
    write_csv(make_results(), str(out_path))
    with open(out_path, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["playlist_track"] == "Perfect"
    assert rows[0]["artist"] == "Ed Sheeran"
    assert rows[0]["status"] == "Found"
    assert rows[0]["matched_local_file"] == "/music/perfect.mp3"
    assert rows[1]["status"] == "Missing"
    assert rows[1]["matched_local_file"] == ""


def test_write_csv_overwrites_existing_file(tmp_path):
    out_path = tmp_path / "report.csv"
    out_path.write_text("old content")
    write_csv(make_results(), str(out_path))
    content = out_path.read_text()
    assert "old content" not in content
    assert "playlist_track" in content
