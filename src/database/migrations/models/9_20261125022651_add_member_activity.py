from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "memberactivitymessageevent" (
    "id" UUID NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_memberactiv_guild_i_e0055c" ON "memberactivitymessageevent" ("guild_id", "member_id", "created_at");
        CREATE TABLE IF NOT EXISTS "memberactivitysettings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "message_channel_ids" JSONB NOT NULL,
    "voice_channel_ids" JSONB NOT NULL,
    "tracked_category_ids" JSONB NOT NULL,
    "guild_id" BIGINT NOT NULL UNIQUE REFERENCES "guild" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "memberactivityvoicesession" (
    "id" UUID NOT NULL PRIMARY KEY,
    "member_id" BIGINT NOT NULL,
    "channel_id" BIGINT NOT NULL,
    "started_at" TIMESTAMPTZ NOT NULL,
    "ended_at" TIMESTAMPTZ NOT NULL,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_memberactiv_guild_i_d153fa" ON "memberactivityvoicesession" ("guild_id", "member_id", "started_at");
COMMENT ON TABLE "memberactivityvoicesession" IS 'One continuous stretch of counted voice time, in one channel.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "memberactivityvoicesession";
        DROP TABLE IF EXISTS "memberactivitymessageevent";
        DROP TABLE IF EXISTS "memberactivitysettings";"""


MODELS_STATE = (
    "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"
    "T3wg=="
)
