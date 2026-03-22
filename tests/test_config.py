import os
import pytest
from config import load_config, ConfigError


def test_raises_when_library_path_not_set(monkeypatch):
    monkeypatch.delenv("MUSIC_LIBRARY_PATH", raising=False)
    with pytest.raises(ConfigError, match="MUSIC_LIBRARY_PATH is not configured"):
        load_config()


def test_raises_when_library_path_does_not_exist(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path / "nonexistent"))
    with pytest.raises(ConfigError, match="does not exist"):
        load_config()


def test_raises_when_library_path_is_a_file(monkeypatch, tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(f))
    with pytest.raises(ConfigError, match="not a directory"):
        load_config()


def test_raises_when_threshold_is_not_an_integer(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("MATCH_THRESHOLD", "banana")
    with pytest.raises(ConfigError, match="MATCH_THRESHOLD must be an integer"):
        load_config()


def test_raises_when_threshold_out_of_range(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("MATCH_THRESHOLD", "101")
    with pytest.raises(ConfigError, match="between 0 and 100"):
        load_config()


def test_default_threshold_is_85(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    monkeypatch.delenv("MATCH_THRESHOLD", raising=False)
    cfg = load_config()
    assert cfg["threshold"] == 85


def test_returns_absolute_library_path(monkeypatch, tmp_path):
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(tmp_path))
    cfg = load_config()
    assert os.path.isabs(cfg["library_path"])


def test_accepts_relative_library_path(monkeypatch, tmp_path):
    # relative paths should be resolved to absolute
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", ".")
    cfg = load_config()
    assert os.path.isabs(cfg["library_path"])
    assert os.path.isdir(cfg["library_path"])
