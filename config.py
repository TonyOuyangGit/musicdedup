import os
from dotenv import load_dotenv

load_dotenv(override=False)


class ConfigError(Exception):
    pass


def load_config() -> dict:
    library_path = os.environ.get("MUSIC_LIBRARY_PATH")
    if not library_path:
        raise ConfigError("MUSIC_LIBRARY_PATH is not configured.")

    library_path = os.path.abspath(library_path)
    if not os.path.exists(library_path):
        raise ConfigError(f"MUSIC_LIBRARY_PATH does not exist: {library_path}")
    if not os.path.isdir(library_path):
        raise ConfigError(f"MUSIC_LIBRARY_PATH is not a directory: {library_path}")

    threshold_raw = os.environ.get("MATCH_THRESHOLD", "85")
    try:
        threshold = int(threshold_raw)
    except ValueError:
        raise ConfigError(f"MATCH_THRESHOLD must be an integer, got: {threshold_raw!r}")
    if not (0 <= threshold <= 100):
        raise ConfigError(f"MATCH_THRESHOLD must be between 0 and 100, got: {threshold}")

    return {
        "library_path": library_path,
        "threshold": threshold,
        "spotify_client_id": os.environ.get("SPOTIFY_CLIENT_ID"),
        "spotify_client_secret": os.environ.get("SPOTIFY_CLIENT_SECRET"),
    }
