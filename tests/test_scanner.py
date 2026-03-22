import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scanner import scan_library, SUPPORTED_EXTENSIONS


def make_music_file(directory: Path, filename: str) -> Path:
    """Create a dummy file with a supported extension."""
    path = directory / filename
    path.write_bytes(b"fake audio data")
    return path


def test_returns_empty_list_for_empty_folder(tmp_path):
    assert scan_library(str(tmp_path)) == []


def test_ignores_unsupported_file_extensions(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(b"img")
    (tmp_path / "notes.txt").write_text("x")
    assert scan_library(str(tmp_path)) == []


def test_reads_id3_tags_when_available(tmp_path, mocker):
    mp3 = make_music_file(tmp_path, "track.mp3")
    mock_tags = MagicMock()
    mock_tags.get = MagicMock(side_effect=lambda k, d=None: {
        "title": ["Perfect"],
        "artist": ["Ed Sheeran"],
    }.get(k, d))
    mocker.patch("scanner.mutagen.File", return_value=mock_tags)

    results = scan_library(str(tmp_path))
    assert len(results) == 1
    assert results[0]["title"] == "Perfect"
    assert results[0]["artist"] == "Ed Sheeran"
    assert os.path.isabs(results[0]["filepath"])


def test_falls_back_to_filename_when_no_tags(tmp_path, mocker):
    make_music_file(tmp_path, "Ed Sheeran - Perfect.mp3")
    mocker.patch("scanner.mutagen.File", return_value=None)

    results = scan_library(str(tmp_path))
    assert results[0]["title"] == "Perfect"
    assert results[0]["artist"] == "Ed Sheeran"


def test_filename_fallback_no_hyphen_uses_full_stem_as_title(tmp_path, mocker):
    make_music_file(tmp_path, "Perfect.mp3")
    mocker.patch("scanner.mutagen.File", return_value=None)

    results = scan_library(str(tmp_path))
    assert results[0]["title"] == "Perfect"
    assert results[0]["artist"] == ""


def test_skips_file_and_warns_when_mutagen_raises(tmp_path, mocker, capsys):
    make_music_file(tmp_path, "bad.mp3")
    mocker.patch("scanner.mutagen.File", side_effect=Exception("corrupted"))

    results = scan_library(str(tmp_path))
    assert results == []
    captured = capsys.readouterr()
    assert "Warning" in captured.out or "Warning" in captured.err


def test_scans_subdirectories_recursively(tmp_path, mocker):
    sub = tmp_path / "subfolder"
    sub.mkdir()
    make_music_file(sub, "song.flac")
    mocker.patch("scanner.mutagen.File", return_value=None)

    results = scan_library(str(tmp_path))
    assert len(results) == 1


def test_supported_extensions_includes_expected_formats():
    for ext in [".mp3", ".flac", ".m4a", ".aiff", ".wav", ".ogg"]:
        assert ext in SUPPORTED_EXTENSIONS
