# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "staffmemberroleoverride" (
    "id" UUID NOT NULL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "role_id" BIGINT NOT NULL,
    CONSTRAINT "uid_staffmember_guild_i_1803c3" UNIQUE ("guild_id", "member_id")
);
CREATE INDEX IF NOT EXISTS "idx_staffmember_guild_i_6ac95b" ON "staffmemberroleoverride" ("guild_id");
COMMENT ON TABLE "staffmemberroleoverride" IS 'Pins a member with several configured quota roles to the one that should apply to them.';
        CREATE TABLE IF NOT EXISTS "staffmessageevent" (
    "id" UUID NOT NULL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_staffmessag_guild_i_a21690" ON "staffmessageevent" ("guild_id", "member_id", "created_at");
        CREATE TABLE IF NOT EXISTS "staffrolequota" (
    "id" UUID NOT NULL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "role_id" BIGINT NOT NULL,
    "voice_minutes_required" INT NOT NULL,
    "messages_required" INT NOT NULL,
    "mode" VARCHAR(3) NOT NULL,
    CONSTRAINT "uid_staffrolequ_guild_i_16f8e8" UNIQUE ("guild_id", "role_id")
);
CREATE INDEX IF NOT EXISTS "idx_staffrolequ_guild_i_499da5" ON "staffrolequota" ("guild_id");
COMMENT ON COLUMN "staffrolequota"."mode" IS 'ANY: any\nALL: all';
        CREATE TABLE IF NOT EXISTS "staffstatssettings" (
    "guild_id" BIGSERIAL NOT NULL PRIMARY KEY,
    "responsible_role_id" BIGINT,
    "report_channel_id" BIGINT,
    "message_channel_ids" JSONB NOT NULL,
    "voice_channel_ids" JSONB NOT NULL,
    "et_substitution_penalty" DOUBLE PRECISION NOT NULL DEFAULT 1.25,
    "last_report_sent_date" DATE
);
        CREATE TABLE IF NOT EXISTS "staffvoicesegment" (
    "id" UUID NOT NULL PRIMARY KEY,
    "guild_id" BIGINT NOT NULL,
    "member_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "started_at" TIMESTAMPTZ NOT NULL,
    "ended_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_staffvoices_guild_i_30234f" ON "staffvoicesegment" ("guild_id", "member_id", "started_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "staffvoicesegment";
        DROP TABLE IF EXISTS "staffmessageevent";
        DROP TABLE IF EXISTS "staffmemberroleoverride";
        DROP TABLE IF EXISTS "staffrolequota";
        DROP TABLE IF EXISTS "staffstatssettings";"""


MODELS_STATE = (
    "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"
    "qdvLr/8Bh2EMNQ=="
)
