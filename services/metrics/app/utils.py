"""ISO 8601 datetime parsing compatible with Python 3.9+.

Python 3.9's datetime.fromisoformat() doesn't support the 'Z' suffix.
This module provides a drop-in replacement that handles it.
"""

from __future__ import annotations

from datetime import datetime, timezone


def parse_iso(value: str) -> datetime:
    """Parse an ISO 8601 datetime string, handling 'Z' suffix for UTC.

    Python 3.9 does not support 'Z' in fromisoformat(); this normalises
    it to '+00:00' before parsing.
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
