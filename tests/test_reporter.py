import csv
from matcher import MatchResult, CandidateMatch
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
        assert reader.fieldnames == [
            "playlist_track", "artist", "status", "matched_local_file", "match_score"
        ]


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
