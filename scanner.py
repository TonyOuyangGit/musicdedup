import os
import mutagen

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".aiff", ".wav", ".ogg"}

_SENTINEL = object()  # distinguishes "mutagen error" from "no tags"


def _read_tags(filepath: str):
    """Return {title, artist} from embedded tags, None if no tags, or _SENTINEL on error."""
    try:
        tags = mutagen.File(filepath, easy=True)
    except Exception as e:
        print(f"Warning: could not read tags for {filepath!r}: {e}", flush=True)
        return _SENTINEL

    if not tags:
        return None

    title = str(tags.get("title", [""])[0]).strip()
    artist = str(tags.get("artist", [""])[0]).strip()

    if not title and not artist:
        return None

    return {"title": title, "artist": artist}


def _parse_filename(filepath: str) -> dict:
    """Extract title and artist from filename stem."""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    if " - " in stem:
        artist, _, title = stem.partition(" - ")
        return {"title": title.strip(), "artist": artist.strip()}
    return {"title": stem.strip(), "artist": ""}


def scan_library(library_path: str) -> list[dict]:
    """Walk library_path and return a list of {title, artist, filepath} dicts."""
    results = []
    for dirpath, _dirnames, filenames in os.walk(library_path):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            filepath = os.path.abspath(os.path.join(dirpath, filename))
            tags = _read_tags(filepath)
            if tags is _SENTINEL:
                # mutagen raised — skip this file entirely per spec
                continue
            if tags:
                entry = {**tags, "filepath": filepath}
            else:
                # no tags — fall back to filename parsing
                parsed = _parse_filename(filepath)
                entry = {**parsed, "filepath": filepath}
            results.append(entry)
    return results
