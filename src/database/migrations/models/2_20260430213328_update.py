# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "channelnote" (
    "id" UUID NOT NULL PRIMARY KEY,
    "discord_id" BIGINT NOT NULL UNIQUE,
    "enabled" BOOL NOT NULL DEFAULT True,
    "content" VARCHAR(1024) NOT NULL,
    "header" VARCHAR(128) NOT NULL,
    "footer" VARCHAR(128) NOT NULL,
    "every" VARCHAR(4) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "channelnote"."every" IS 'H_1: h_1\nH_6: h_6\nH_12: h_12\nD_1: d_1\nD_7: d_7';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "channelnote";"""


MODELS_STATE = (
    "eJztmf9v2jgUwP+VKD+1UocgUOCq00lQuJXTCqcO7k4bU2RiA1YTmyX2NlT1fz8/JyEkJB"
    "l0V5Xu4Ic2eV/s54/9XmLnwfQ4Jm5QuV4ixog75IKYV8aDyZAHF3nqC8NEq1WiBIFAM1fb"
    "O6Ehiw1ngfCRI5RqjtyAKBEmgePTlaCcKSmTrgtC7ihDyhaJSDL6WRJb8AURS+IrxcdPSk"
    "wZJt9IEN+u7u05JS5OBU0x9K3ltlivtGwyGfR+15bQ3cx2uCs9lliv1mLJ2cZcSoor4AO6"
    "BWHER4LgrWFAlNGgY1EYsRIIX5JNqDgRYDJH0gUY5q9zyRxgYOie4E/jN/MAPA5ngJYyAS"
    "weHsNRJWPWUhO6ur7p3J3Vm+d6lDwQC18rNRHzUTsigUJXzTUBiWngcB/beUC7dDFgIh9p"
    "2i+DVoX8PFBjWE8jqAJS/978Yln1esuq1pvty0arddmutpWtDmlX1SrB3h28HQzHMFKuMi"
    "DMDhAA8YQwYTDePLycuwSxfL5bXhm4M+X2FLqxIMGb5GvMdwP8v16h3dHoHQTtBcFnN2SX"
    "ATec3Hb7d2c1vYiVERUFPFWngoQLLM1TVTA/H+aWSwamCv+5WP7gWvXQN9slbCGW6rZWtR"
    "oldP/q3OkSAGbnGayRzoqUaZZLgjDxD0GZeLxSklZ7H5BWu5gj6NIY51w9DA/CmHicMCaV"
    "8gvx1/kU+0x6muRABYWYQ3YLZuz8wkDNG7t2ZSzt2pTd2E24asJVzdJCa8p6oMeg79ktuG"
    "qZT5iAfcpBcS3YKQSOTwCOjXLqak9pBPVIQW1NeWbg48i1El8c6dpWY8Aj5q6jR2AJ2/Hg"
    "tv9+3Ln9M/U063XGfdBYWrrOSM+amYnYNGL8PRjfGHBrfBgN+9n3t43d+IMJMSEpuM34Vx"
    "vhrdejWBqDSU2sXOEnTmza8zSxLzqxOnjYDc3vt17jQTBDzv1XpN7EdzTc4kW2uyrP8rIS"
    "xNBCzwqwhSijnWKP+x6RvpmziYxVF2UbSLxl9L3Noxm1aOh2KtlKmVFP2ZTdkZWCrN72Ag"
    "MZMiC+QZmhtpcGbIFmKCDaqiOEH1yZF6dN6GkT+rNuQo+kXLyVNJM3KUVpqVhsTL5bKCaQ"
    "6gVVYkt3WImgMylIMGVvNr8pM9SPYuNMTej5ldELl2DYzKBXCfVznxBbvRlhqvqILDsel0"
    "wYfK61RqyFfrXzEgWRt4rOo9IrbiAyyG/jGYpaWQ7um3tRGv0/Um+32B1JMkIm5OWilpem"
    "oowtTpl4ysRTJv5wJnaIT51lXi5GmtJsRInN0Xx/+YkWplVrtBrterOxWY8bSdkyLFpyCb"
    "cvxA8gpB14xUeFWy6v86zQurzc47BKWRUeV2ld+sAKUuMAiJH56wRYq1b3Ovyvlpz9V3dO"
    "/Io+o/zxfjQ89DPKhKkBfsTUEReGSwPx6TixllCEUadOfmJ4Z7edf7Jcr9+NutltLjTQfe"
    "ld1+O/u7guSw=="
)
