# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

# NOTE: aerich could not auto-generate this one (it refused to change a primary key's type —
# "Does not support change primary_key(StaffStatsSettings.id) field type, you may need to do it
# manually"), since `guild_id` goes from being the BIGSERIAL primary key itself to a plain
# BIGINT foreign key column, with a new separate `id` UUID column taking over as primary key.
# Hand-written below; `MODELS_STATE` is still the aerich-generated snapshot (derived from the
# Python models, not the DB diff, so it doesn't need the same correction).

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "staffstatssettings" DROP CONSTRAINT "staffstatssettings_pkey";
        ALTER TABLE "staffstatssettings" ALTER COLUMN "guild_id" DROP DEFAULT;
        ALTER TABLE "staffstatssettings" ADD COLUMN "id" UUID NOT NULL DEFAULT gen_random_uuid();
        ALTER TABLE "staffstatssettings" ADD PRIMARY KEY ("id");
        ALTER TABLE "staffstatssettings" ADD CONSTRAINT "uid_staffstatssettings_guild_id" UNIQUE ("guild_id");
        ALTER TABLE "staffstatssettings" ADD CONSTRAINT "fk_staffsta_guild_29819036" FOREIGN KEY ("guild_id") REFERENCES "guild" ("id") ON DELETE CASCADE;
        DROP SEQUENCE IF EXISTS "staffstatssettings_guild_id_seq";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "staffstatssettings" DROP CONSTRAINT IF EXISTS "fk_staffsta_guild_29819036";
        ALTER TABLE "staffstatssettings" DROP CONSTRAINT IF EXISTS "uid_staffstatssettings_guild_id";
        ALTER TABLE "staffstatssettings" DROP CONSTRAINT "staffstatssettings_pkey";
        ALTER TABLE "staffstatssettings" DROP COLUMN "id";
        ALTER TABLE "staffstatssettings" ADD PRIMARY KEY ("guild_id");"""


MODELS_STATE = (
    "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"
    "vdh5zcqCyGc7mXnV5eXxf2TJOxk="
)
