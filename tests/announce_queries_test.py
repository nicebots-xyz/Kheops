# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from tortoise import Tortoise
from tortoise_extensions.s3 import MemoryStorage, init_storages

from src.database.models import Announcement, AnnouncementStatus
from src.extensions.announce.queries import (
    cancel_announcement,
    claim_for_sending,
    create_announcement,
    due_announcement_ids,
    fail_interrupted_sends,
    record_send_result,
    update_announcement,
)

GUILD_ID = 1
PAST = datetime(2026, 1, 1, tzinfo=UTC)

#: An in-memory SQLite database by default, which CI can run without a server.
DB_URL = os.environ.get("ANNOUNCE_TEST_DB_URL", "sqlite://:memory:")


def _run[T](test: Callable[[], Awaitable[T]]) -> T:
    async def run() -> T:
        await Tortoise.init(db_url=DB_URL, modules={"models": ["src.database.models"]})
        await Tortoise.generate_schemas()
        init_storages({"models": MemoryStorage()})
        try:
            return await test()
        finally:
            await Announcement.all().delete()
            await Tortoise.close_connections()

    return asyncio.run(run())


async def _create(*, scheduled_for: datetime | None = PAST, image: bytes | None = None) -> Announcement:
    return await create_announcement(
        guild_id=GUILD_ID,
        channel_id=2,
        title="Title",
        content="Content",
        footer=None,
        role_ids_to_mention=[],
        image=image,
        image_filename="image.png" if image is not None else None,
        scheduled_for=scheduled_for,
        created_by_id=3,
    )


async def _update(announcement: Announcement, *, image: bytes | None = None) -> Announcement | None:
    return await update_announcement(
        announcement.id,
        GUILD_ID,
        channel_id=2,
        title="Edited",
        content="Content",
        footer=None,
        role_ids_to_mention=[],
        scheduled_for=datetime.now(tz=UTC) + timedelta(days=1),
        image=image,
        image_filename="new.png" if image is not None else None,
    )


def test_instant_announcement_is_created_claimed() -> None:
    """Test that an announcement without a date is created already claimed for its sender."""

    async def test() -> None:
        announcement = await _create(scheduled_for=None)
        assert announcement.status == AnnouncementStatus.SENDING
        assert await claim_for_sending(announcement.id) is None

    _run(test)


def test_concurrent_claims_send_once() -> None:
    """Test that only one of several racing senders claims a scheduled announcement."""

    async def test() -> None:
        announcement = await _create()
        claims = await asyncio.gather(*(claim_for_sending(announcement.id) for _ in range(5)))
        assert sum(claim is not None for claim in claims) == 1

    _run(test)


def test_claim_checks_guild() -> None:
    """Test that an announcement cannot be claimed through another guild."""

    async def test() -> None:
        announcement = await _create()
        assert await claim_for_sending(announcement.id, GUILD_ID + 1) is None
        assert await claim_for_sending(announcement.id, GUILD_ID) is not None

    _run(test)


def test_cancel_and_edit_lose_to_a_claim() -> None:
    """Test that a claimed announcement can no longer be cancelled or edited."""

    async def test() -> None:
        announcement = await _create()
        claimed = await claim_for_sending(announcement.id)
        assert claimed is not None
        assert not await cancel_announcement(announcement.id, GUILD_ID)
        assert await _update(announcement) is None
        await record_send_result(claimed, message_id=42)
        sent = await Announcement.get(id=announcement.id)
        assert (sent.status, sent.title, sent.message_id) == (AnnouncementStatus.SENT, "Title", 42)

    _run(test)


def test_claim_loses_to_a_cancel() -> None:
    """Test that a cancelled announcement is never claimed afterwards."""

    async def test() -> None:
        announcement = await _create()
        assert await cancel_announcement(announcement.id, GUILD_ID)
        assert await claim_for_sending(announcement.id) is None
        assert announcement.id not in await due_announcement_ids(datetime.now(tz=UTC))

    _run(test)


def test_edit_replaces_image_only_when_given() -> None:
    """Test that editing keeps the stored image unless a new one is given, then replaces it."""

    async def test() -> None:
        announcement = await _create(image=b"old")
        old_image = announcement.image

        kept = await _update(announcement)
        assert kept is not None
        assert (await kept.image.read(), kept.image_filename) == (b"old", "image.png")

        replaced = await _update(kept, image=b"new")
        assert replaced is not None
        assert (await replaced.image.read(), replaced.image_filename) == (b"new", "new.png")
        assert not await old_image.exists()

    _run(test)


def test_due_announcement_ids() -> None:
    """Test that only scheduled announcements whose time has come are due."""

    async def test() -> None:
        due = await _create()
        await _create(scheduled_for=datetime.now(tz=UTC) + timedelta(days=1))
        await _create(scheduled_for=None)
        assert await due_announcement_ids(datetime.now(tz=UTC)) == [due.id]

    _run(test)


def test_interrupted_sends_fail() -> None:
    """Test that announcements left sending by a stopped process are marked as failed."""

    async def test() -> None:
        announcement = await _create(scheduled_for=None)
        assert await fail_interrupted_sends() == 1
        assert (await Announcement.get(id=announcement.id)).status == AnnouncementStatus.FAILED

    _run(test)
