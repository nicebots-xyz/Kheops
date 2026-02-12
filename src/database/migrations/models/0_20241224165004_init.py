# Copyright Communauté Les Frères Poulain 2025, 2026
# SPDX-License-Identifier: MIT

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "guild" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY
);
COMMENT ON TABLE "guild" IS 'User model.';
CREATE TABLE IF NOT EXISTS "user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY
);
COMMENT ON TABLE "user" IS 'User model.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztVV1P2zAU/StWnkACVNKWdryloLFOG0jdmCZRFLmxm1okdrCdDYT633ftOB9tKWVT+z"
    "I1L1XOvT4+PtenefFSQWiiTm4Vld45evFwlsGvg70j5HGc0hopGgHWeJJYPHcA44Q+UQXQ"
    "3T284onSEkca3qc4URSg7CGcMpoQu09Jy4hZnHP2mJt3LXPTSugU54lZzPMkqdhJ3WFwJ6"
    "HkJ5MwEkme8pqXiAhkMB7XTDHlVGLd5LKqQv2cWUUDFg+5/miVQjES3JyEca2s8Ng0HX/w"
    "/Xa757faZ/1up9fr9lt96LVyVku9uT2SiiTLNBO8FpM965ng1dawiVccpJZU7GqFDa+G19"
    "9NgwBnC/cNMJ8vndQzQ0J2YCdjPuYjmkmqKJwAYWTmhRhHekYRwTBGrKjtCjSsn+SaqjE/"
    "rp4xR/Awgg5A3OE5umQqEpIUNMPLk6I+lZSGkaSEwR6uM0hFzjUSU1tFZdXsaxfPsHKrQV"
    "3K8nQ9gWt4ncMYMnVXq7p+qZ8uIcIXS4g5/TK0MKSmj/UtDbWIKSiQ5aIJjh5+Y0nCFRVV"
    "ZWlzMzCXp6ucuURsSl7R2YxeXCL77O2zt8/eX2cvoJJFs3eFz7U204cr6L+J3+bs+aedXq"
    "ffPutUkauQLSXt1VQ5om1ctdr/X1Qqo7M5hMrQ9VMoWzaNoUG/YRbl8sVhXMywXDuNFD+F"
    "CeWxNtfX73bf6z2QvOH9j2B08SkYHQDh4eJ/3bUr+UXNDKg20oRnRyY66h0beNpqbddAIF"
    "xroK0tGgjiNC1SsQsTG/T/ZOTnbzfX64x8r2+3HKp3hEX6CCVM6fs3XDT7mXKq1GPSNO/g"
    "a/Bz2deLLzcDA2VC6VhaFkswAI9XPytO3Pa+JvM/oWs7eQ=="
)
