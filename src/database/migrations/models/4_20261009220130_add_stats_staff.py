# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "staffmemberroleoverride" (
    "id" UUID NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "role_id" BIGINT NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_staffmember_guild_i_1803c3" UNIQUE ("guild_id", "member_id")
);
COMMENT ON TABLE "staffmemberroleoverride" IS 'Pins a member holding several quota roles to the one that applies to them.';
        CREATE TABLE IF NOT EXISTS "staffmessageevent" (
    "id" UUID NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_staffmessag_guild_i_a21690" ON "staffmessageevent" ("guild_id", "member_id", "created_at");
        CREATE TABLE IF NOT EXISTS "staffrolequota" (
    "id" UUID NOT NULL PRIMARY KEY,
    "role_id" BIGINT NOT NULL,
    "voice_minutes_required" INT NOT NULL,
    "messages_required" INT NOT NULL,
    "mode" VARCHAR(3) NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_staffrolequ_guild_i_16f8e8" UNIQUE ("guild_id", "role_id")
);
COMMENT ON COLUMN "staffrolequota"."mode" IS 'ANY: any\nALL: all';
        CREATE TABLE IF NOT EXISTS "staffstatssettings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "responsible_role_id" BIGINT,
    "report_channel_id" BIGINT,
    "message_channel_ids" JSONB NOT NULL,
    "voice_channel_ids" JSONB NOT NULL,
    "et_substitution_penalty" DOUBLE PRECISION NOT NULL DEFAULT 1.25,
    "guild_id" BIGINT NOT NULL UNIQUE REFERENCES "guild" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "staffvoicesession" (
    "id" UUID NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "started_at" TIMESTAMPTZ NOT NULL,
    "ended_at" TIMESTAMPTZ NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_staffvoices_guild_i_037f95" ON "staffvoicesession" ("guild_id", "member_id", "started_at");
COMMENT ON TABLE "staffvoicesession" IS 'One continuous stretch of counted voice time, in one channel.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "staffvoicesession";
        DROP TABLE IF EXISTS "staffmessageevent";
        DROP TABLE IF EXISTS "staffrolequota";
        DROP TABLE IF EXISTS "staffmemberroleoverride";
        DROP TABLE IF EXISTS "staffstatssettings";"""


MODELS_STATE = (
    "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"
)
