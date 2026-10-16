# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "absence" (
    "id" UUID NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "start_date" DATE NOT NULL,
    "end_date" DATE NOT NULL,
    "reason" VARCHAR(500) NOT NULL DEFAULT '',
    "created_by_id" BIGINT NOT NULL,
    "announce_channel_id" BIGINT,
    "announce_message_id" BIGINT,
    "cancelled_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_absence_guild_i_837fbd" ON "absence" ("guild_id", "member_id");
        CREATE TABLE IF NOT EXISTS "absencesettings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "allowed_role_ids" JSONB NOT NULL,
    "announce_channel_id" BIGINT,
    "responsible_role_id" BIGINT,
    "guild_id" BIGINT NOT NULL UNIQUE REFERENCES "guild" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "absencesettings";
        DROP TABLE IF EXISTS "absence";"""


MODELS_STATE = (
    "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"
)
