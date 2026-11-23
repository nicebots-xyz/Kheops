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
    "image_data" BYTEA,
    "image_filename" VARCHAR(255),
    "scheduled_for" TIMESTAMPTZ,
    "status" VARCHAR(9) NOT NULL DEFAULT 'sent',
    "message_id" BIGINT,
    "created_by_id" BIGINT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sent_at" TIMESTAMPTZ,
    "guild_id" BIGINT NOT NULL REFERENCES "guild" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_announcemen_guild_i_ffe243" ON "announcement" ("guild_id", "status");
COMMENT ON COLUMN "announcement"."status" IS 'SCHEDULED: scheduled\nSENT: sent\nCANCELLED: cancelled\nFAILED: failed';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "announcesettings";
        DROP TABLE IF EXISTS "announcement";"""


MODELS_STATE = (
    "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"
)
