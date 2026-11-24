# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

import re
from collections.abc import Iterable
from datetime import date, datetime, time
from pathlib import PurePath

from src.database.models import (
    IMAGE_EXTENSIONS_ANNOUNCEMENT,
    IMAGE_FILENAME_MAX_LENGTH_ANNOUNCEMENT,
    AnnounceSettings,
)

DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")
_DEFAULT_IMAGE_STEM = "image"


def parse_date(value: str) -> date:
    """Parse a date in `DATE_FORMAT`.

    Args:
        value: The text typed by the member.

    Returns:
        The parsed date.

    Raises:
        ValueError: If `value` is not in `DATE_FORMAT`.

    """
    return datetime.strptime(value.strip(), DATE_FORMAT).date()  # noqa: DTZ007 - .date() discards the naive time


def parse_time(value: str) -> time:
    """Parse a 24h time in `TIME_FORMAT`.

    Args:
        value: The text typed by the member.

    Returns:
        The parsed time.

    Raises:
        ValueError: If `value` is not in `TIME_FORMAT`.

    """
    return datetime.strptime(value.strip(), TIME_FORMAT).time()  # noqa: DTZ007 - .time() discards the naive date


def can_schedule(member_role_ids: Iterable[int], *, is_admin: bool, settings: AnnounceSettings) -> bool:
    """Tell whether a member can schedule an announcement for later.

    Args:
        member_role_ids: The IDs of the member's roles.
        is_admin: Whether the member is an administrator, who always can.
        settings: The guild's settings, holding the other roles allowed to.

    Returns:
        Whether the member can schedule an announcement.

    """
    if is_admin:
        return True
    return not set(settings.allowed_role_ids).isdisjoint(member_role_ids)


def sanitize_image_filename(filename: str) -> str | None:
    """Turn an uploaded filename into one safe for an `attachment://` reference.

    Args:
        filename: The filename as uploaded.

    Returns:
        The sanitized filename, or `None` if its extension is not an accepted image type.

    """
    path = PurePath(filename.replace("\\", "/"))
    suffix = path.suffix.lower()
    if suffix not in IMAGE_EXTENSIONS_ANNOUNCEMENT:
        return None
    stem = _UNSAFE_FILENAME_CHARS.sub("_", path.stem).strip("_") or _DEFAULT_IMAGE_STEM
    return stem[: IMAGE_FILENAME_MAX_LENGTH_ANNOUNCEMENT - len(suffix)] + suffix


__all__ = (
    "DATE_FORMAT",
    "TIME_FORMAT",
    "can_schedule",
    "parse_date",
    "parse_time",
    "sanitize_image_filename",
)
