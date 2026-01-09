# Copyright (c) Communauté Les Frères Poulain
# SPDX-License-Identifier: MIT

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "dormeur" (
    "id" UUID NOT NULL PRIMARY KEY,
    "discord_id" BIGINT NOT NULL UNIQUE
);
COMMENT ON TABLE "dormeur" IS 'Dormeur model.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "dormeur";"""


MODELS_STATE = (
    "eJztl2tv2jAUhv+KlU+t1CIaoLBqmgRF65g2KnVjmlQqZGITrCY29WVrVfHf5+MEAgmkl7"
    "Vat5UPvZzzHvucJ34tcuvFgtBIVbpCxtRI7wjdehzH1P6RT+0hD89mWQICGo8jpyUrorHS"
    "Egfahic4UtSGCFWBZDPNBAdxuiJy61SghojAFjEeFtNDPuRndCapolwrhJFRVCLGkZ5SRL"
    "DtACvqVG2tpTqC5QxnV4aOtAipVcFU5xc2zDih11Qt/p1djiaMRmRtaEZgARcf6ZuZiw0G"
    "ve57p4RWx6NARCbmmXp2o6eCL+XGMFKBGsiFlFOJNSUrOLiJohTcIpR0bANaGrpslWQBQi"
    "fYRADVezsxPACWyO0EP+rvvAJm2CWHNg0FgsMjYpYnzD5PpspmdlEPtjr+0D7bqR3uuimF"
    "0qF0SUfEm7tC+wSSUsc1A0mYCoQko01AOyzscb0Z6XpdDq1t+XmgLmA9jqBtyP7af+P7tV"
    "rTr9YOW416s9loVVtW61oqppol2Du9k17/K0wqrJMSh0FgPodzO7lcAQ6BMQ4uf2LLrJAR"
    "vtimLaZiP85HMMehAwZzQ8PpnXBiWM43a4nSqyJcSu68KAZg9S23xEruYVcEGxtN1ZDvLz"
    "9DjuyHEbRjH+juEeomRzBZptetJPmJpHQUSEqY3SNVtmNhuEZi4rJokYV9XfEUq7Tadhcz"
    "E29fIBVsXuMZLrUyD97Xe6mN/g/rFS+7F2JGcMImL7p4qRXNQvHqxFcnvjrxt53YppIF00"
    "1eTDOlbsSZ5i4/bn8oT3w2/6GD6R/Um/VW7bC+PI/LSNkx3HbkMm4/qFTQUgHe8RTLzfRW"
    "SnIIbeOP+Ya7CGQQs4PzRBRjfD2KKA81HHC/0Shh9q195t4crGp33cD9NOUnOQCbgQRrPA"
    "BiKv87AR5Uq/cAaFVbAbrcOkC7o6aJB9chfvxy2t8McaUkB3LA7YDnhAV6D0VM6YuXibWE"
    "IkwNTcdKXUWr8HY+t7/nuR5/Ou3kX3Nhgc6ffuua/wJGu6LT"
)
