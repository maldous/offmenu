"""Prospective acquisition/route policy. Never redact historical attribution or map links."""
import json
from importlib.resources import files
from urllib.parse import urlsplit

RETIRED = frozenset(json.loads(files(__package__).joinpath("retired_direct_sources.json").read_text()))
_IDS = frozenset(key.casefold() for key in RETIRED) | frozenset(
    key.split(":", 1)[1].casefold() for key in RETIRED if key.startswith("discovery:")
)
REASON = "direct-source-retired"


def retired(source_id, acquisition_url=None):
    """Match only the direct ID or the actual collection endpoint, not its provenance."""
    if isinstance(source_id, str) and source_id.casefold() in _IDS:
        return True
    if not isinstance(acquisition_url, str):
        return False
    try:
        host = (urlsplit(acquisition_url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False  # Caller retains responsibility for rejecting invalid locators.
    return any(host == name or host.endswith("." + name) for name in ("openstreetmap.org", "osm.org"))


def active_ids(ids):
    return [key for key in ids if not retired(key)]


def active_providers(rows):
    """A provider may have both active and retired primary discovery references."""
    for row in rows:
        ids = row.get("source_ids", [])
        selected = active_ids(ids)
        if not ids or selected:
            yield {**row, "source_ids": selected} if ids != selected else row
