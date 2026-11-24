# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "announcesettings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "allowed_role_ids" JSONB NOT NULL,
    "guild_id" BIGINT NOT NULL UNIQUE REFERENCES "guild" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "announcement" (
    "id" UUID NOT NULL PRIMARY KEY,
    "channel_id" BIGINT NOT NULL,
    "title" VARCHAR(256) NOT NULL,
    "content" VARCHAR(3072) NOT NULL,
    "footer" VARCHAR(512),
    "role_ids_to_mention" JSONB NOT NULL,
    "image" VARCHAR(1024),
    "image_filename" VARCHAR(64),
    "scheduled_for" TIMESTAMPTZ,
    "status" VARCHAR(9) NOT NULL,
    "message_id" BIGINT,
    "created_by_id" BIGINT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sent_at" TIMESTAMPTZ,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_announcemen_guild_i_ffe243" ON "announcement" ("guild_id", "status");
COMMENT ON COLUMN "announcement"."status" IS 'SCHEDULED: scheduled\nSENDING: sending\nSENT: sent\nCANCELLED: cancelled\nFAILED: failed';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "announcesettings";
        DROP TABLE IF EXISTS "announcement";"""


MODELS_STATE = (
    "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"
    "zLdZ2g7WRtXLz/8Dac4Fqg=="
)
