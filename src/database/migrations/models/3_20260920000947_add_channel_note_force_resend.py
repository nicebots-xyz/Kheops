# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "channelnote" ADD "force_resend" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "channelnote" DROP COLUMN "force_resend";"""


MODELS_STATE = (
    "eJztmf9v2jgUwP+VKD9RqUMQKHDVdBIUbuW0wtTB7rQxRSY2YDWxWeJsQ1X/9/NzvpGQZN"
    "Bdr3QHP7ThfXGeP/Z7yTP3usMxsb3q1QoxRuwRF0S/1O51hhy4yFOfazparxMlCASa28re"
    "CgxZZDj3hIssIVULZHtEijDxLJeuBeVMSplv2yDkljSkbJmIfEa/+MQUfEnEirhS8emzFF"
    "OGyXfiRV/Xd+aCEhungqYY7q3kptislWw6Hfb/UJZwu7lpcdt3WGK93ogVZ7G571NcBR/Q"
    "LQkjLhIEb00DogwnHYmCiKVAuD6JQ8WJAJMF8m2Aob9e+MwCBpq6E/xp/q4fgMfiDNBSJo"
    "DF/UMwq2TOSqrDra6uu7eVRutMzZJ7YukqpSKiPyhHJFDgqrgmIDH1LO5iMw9ojy6HTOQj"
    "Tftl0MqQnwZqBOtxBGVA8t+r3wyj0WgbtUarc9Fsty86tY60VSHtqtol2HvDN8PRBGbKZQ"
    "YE2QECIJ4QJgzmm4eXc5sgls93yysDdy7dHkM3EiR4k3yN+MbA/+0d2huP30LQjud9sQN2"
    "GXCj6U1vcFupq00sjago4LngrkVMucMJOxRq1vU/JHtobXwWtPKmggS5m6YqHw5uPtItlw"
    "xNGf5TwfzJMuCg76ZN2FKs5Nd6zWiW0P3QvVXVFczOMlhDnREq0yxXBGHiHoIy8XihJI3O"
    "PiCNTjFH0GWzXb5nHIQx8ThhTB5CX4m7yac4YL6jSA5lUIhZZPdZFDk/M1D92qxfaiuzPm"
    "PXZguuWnBVN5TQmLE+6DHo+2Ybrtr6IxZgn3JQXAt2CoHlEoBjopy62pcaQR1SUFtTnhn4"
    "OHStRhdHurflHPCY2Zvw7aKE7WR4M3g/6d68Sz3N+t3JADSGkm4y0korsxDxINpfw8m1Bl"
    "+1j+PRIPtqHNtNPuoQE/IFNxn/ZiK89eYZSSMwqYX11/iRC5v2PC3ssy6sCh4azcXdVocE"
    "gjmy7r4h2eTsaLjBi2x3VY7hZCWIoaVaFWALUYZNeJ+7DvFdPac/j1TnZb053jL6UV+uhy"
    "NqapxqtlJm1DM2Y7dkrd6dhachzfeIq1Gmyc5dg+5yjjyirLpCuN6lfn7q70/9/a/a3x9J"
    "uXjj00zepBSlpWIZm/ywUEwh1QuqxJbusBJB574g3oy9ij8zpskPxVpFLujZpdYPtmAwzL"
    "BfDfQLlxBTvhlhKu8RWnYd7jOh8YXSapEW7qucV8gLvWV0DvWd4gFCg/wxnqColeXgvrkX"
    "ptH/I/V2i92RJCNkQl4uKnlpKvqRxSkTT5l4ysSfzsQucam1ysvFUFOajSixOZqftn6hjW"
    "nUm+1mp9FqxvsxlpRtw6Itl3D7SlwPQtqBV3xUuOXyMs8KjYuLPQ6rpFXhcZXSpQ+sIDUO"
    "gBiav0yA9Vptr8P/WsnZf23nxK/oZ5Q/349Hh/6MMmVygp8wtcS5ZlNPfD5OrCUUYdapk5"
    "8IXuWm+3eW69XbcS/b5sIAvefuuh7+AU9OnWI="
)
