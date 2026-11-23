# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from .absence import (
    AVAILABILITY_NOTE_MAX_LENGTH as AVAILABILITY_NOTE_MAX_LENGTH_ABSENCE,
)
from .absence import (
    REASON_MAX_LENGTH as REASON_MAX_LENGTH_ABSENCE,
)
from .absence import (
    Absence,
    AbsenceKind,
    AbsenceSettings,
)
from .announcement import (
    CONTENT_MAX_LENGTH as CONTENT_MAX_LENGTH_ANNOUNCEMENT,
)
from .announcement import (
    FOOTER_MAX_LENGTH as FOOTER_MAX_LENGTH_ANNOUNCEMENT,
)
from .announcement import (
    MAX_ROLES_TO_MENTION as MAX_ROLES_TO_MENTION_ANNOUNCEMENT,
)
from .announcement import (
    TITLE_MAX_LENGTH as TITLE_MAX_LENGTH_ANNOUNCEMENT,
)
from .announcement import (
    Announcement,
    AnnouncementStatus,
    AnnounceSettings,
)
from .channel_note import (
    CONTENT_MAX_LENGTH as CONTENT_MAX_LENGTH_CHANNEL_NOTE,
)
from .channel_note import (
    FOOTER_MAX_LENGTH as FOOTER_MAX_LENGTH_CHANNEL_NOTE,
)
from .channel_note import (
    HEADER_MAX_LENGTH as HEADER_MAX_LENGTH_CHANNEL_NOTE,
)
from .channel_note import (
    SLOTS_PER_DAY as SLOTS_PER_DAY_CHANNEL_NOTE,
)
from .channel_note import (
    SLOTS_PER_WEEK as SLOTS_PER_WEEK_CHANNEL_NOTE,
)
from .channel_note import (
    ChannelNote,
    ChannelNoteEvery,
)
from .dormeur import Dormeur
from .guild import Guild
from .staff_stats import (
    DEFAULT_ET_SUBSTITUTION_PENALTY,
    StaffMemberRoleOverride,
    StaffMessageEvent,
    StaffQuotaMode,
    StaffRoleQuota,
    StaffStatsSettings,
    StaffVoiceSession,
)
from .user import User

__all__ = [
    "AVAILABILITY_NOTE_MAX_LENGTH_ABSENCE",
    "CONTENT_MAX_LENGTH_ANNOUNCEMENT",
    "CONTENT_MAX_LENGTH_CHANNEL_NOTE",
    "DEFAULT_ET_SUBSTITUTION_PENALTY",
    "FOOTER_MAX_LENGTH_ANNOUNCEMENT",
    "FOOTER_MAX_LENGTH_CHANNEL_NOTE",
    "HEADER_MAX_LENGTH_CHANNEL_NOTE",
    "MAX_ROLES_TO_MENTION_ANNOUNCEMENT",
    "REASON_MAX_LENGTH_ABSENCE",
    "SLOTS_PER_DAY_CHANNEL_NOTE",
    "SLOTS_PER_WEEK_CHANNEL_NOTE",
    "TITLE_MAX_LENGTH_ANNOUNCEMENT",
    "Absence",
    "AbsenceKind",
    "AbsenceSettings",
    "AnnounceSettings",
    "Announcement",
    "AnnouncementStatus",
    "ChannelNote",
    "ChannelNoteEvery",
    "Dormeur",
    "Guild",
    "StaffMemberRoleOverride",
    "StaffMessageEvent",
    "StaffQuotaMode",
    "StaffRoleQuota",
    "StaffStatsSettings",
    "StaffVoiceSession",
    "User",
]
