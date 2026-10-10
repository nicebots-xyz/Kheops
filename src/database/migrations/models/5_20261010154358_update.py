# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz
from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "staffstatssettings" ADD "tracked_category_ids" JSONB NOT NULL DEFAULT '[]';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "staffstatssettings" DROP COLUMN "tracked_category_ids";"""


MODELS_STATE = (
    "eJztXFtv47YS/iuEn7JAGiTOtcHBAZzY23WbxNtcek67Wai0RNvESqRXojY1FvnvnaEky7"
    "r6Eju2s8qDY5MzQ/IjOZzhjPS95kiL2d7e5YAKwewbqVjtnHyvCergl7zqXVKjw2FciQWK"
    "dm1NbwaEIiLsesqlpoKqHrU9BkUW80yXDxWXAkqFb9tYKE0g5KIfF/mCf/WZoWSfqQFzoe"
    "LTZyjmwmL/MC/6Ofxi9DizrUSnuYVt63JDjYa67OGh3XyvKbG5rmFK23dETD0cqYEUY3Lf"
    "59Ye8mBdnwnmUsWsiWFgL8NBR0VBj6FAuT4bd9WKCyzWo76NYNT+0/OFiRgQ3RJ+HP23Ng"
    "c8phQILRcKsfj+HIwqHrMurWFTlx8atzuHJ+/0KKWn+q6u1IjUnjUjVTRg1bjGQFrcM6Vr"
    "GXmAXvB+W6h8SJN8KWihy6sBNQJrMQShQ/Dvp5/r9cPD0/r+4cnZ8dHp6fHZ/hnQ6i5lq0"
    "5LYL9o/9K+uceRStgBwe7AAkQ8RpgJHG8evFLajIp8fCe4UuB2gW0RdKOCGN54v0b4jgFf"
    "9gq96HSusNOO5321A+xSwN08XF+0bncO9CIGIq4K8OxJ12QGrHAm5gU1zfqKyM6rG9cCLT"
    "SqWLB3k6jC4eDmQzrBkkITur8qMF+oBhz6j2Ez0VcD+HmwXz8qQfePxq3Wrkj2LgVrWFcP"
    "K5NYDhi1mDsPlDHHliJZP5sFyPpZMY5Yl97tYGfMBWPMUcEYH0LfmDvKR7ElfEcj2YZOUW"
    "Gy7FkUMa8Z0NoH4+CcDIyDR/HBOMFvJ/jtoK4L64+iifUW1jeNU/x2WltgAmZRB8W6IKMI"
    "TJchOAbN0atNqFHcYQW6NcGZAt8KWfeiLxu6tmEMVkfYo9C6KMH2vn3durtvXH9MnGbNxn"
    "0La+q6dJQq3TlJTcRYCPlf+/4DwZ/kr85NK20aj+nu/6phn6ivpCHkk0GtCcszKo2ASUys"
    "P7QWnNgkZzWxa51Y3Xl0NHtfJjwkLOhS88sTBScnUyPrsog2W+XUnXQJFbSvZwWxxV6GTn"
    "hTug7z3VqOfx5V7Zb55tYE0TS/vBZKJFrOXlpTpqofxaO4ZUNtOyuPUOJ7zCVcEPDcCXqX"
    "XeoxTdVQyvXOa7uVf1/592/Vv98QdfGLz1P7JlFRqir6Y5KpiuIBt3qBlpiom09F8K6vmP"
    "cofhr/PQoCf9wiOzCh785JM1iCgZh2cy+o77mMGWAZWRzaCCkbjvSFIrKna0lUi+1q5gH1"
    "Qm7oncN9p1hASJAvYwVKrWwPzrr3wm30Y2y9rLKbYzPGcwGuTq9nOMzpMtdwpc0MCV6Oy2"
    "H8OZMUCnv/2y2zqcYmOzHh1rtDwdda7i2I7YRSN9OIe46WXFQaG3NZqDwPtNBy0NGiWt/Y"
    "YufIRuGi185XXyq6DGhwyfyOwrYel2+Sm8zwYKqhjWVA8wcKvAvkbRk6c9kAaSDhU3kApF"
    "LQdgmQHcHuJXzMCOcdir2bkDoFz/DA2BQ457CSijRyjt1UoryLLSk9TcFJgspATjJNta0+"
    "coGmUsBOBtK2ABLi4ZUbtYnWKwSlgiUitTEiBYP/VBHokM3H5U7WNFuu6By751NsRIYHKV"
    "gsnysXb9qKXrKLF2M/l3WZYFuOg/cKt05rCeHqM35efCeYKnTL0NVKZG54J7kqfKdeUKTg"
    "zmL9XrqM98VvbJQJBuVbEeM7hs3DuchygGKXPo3PosQaggHCsFgQGr9s3F02mq3a83rudb"
    "JeUrGtknSlplopmpyNyVeZvJVrHuwmwlqfK+ugsg62Ub8mArxBQuTcECf5KoxLMf6hg+hb"
    "EluNhl0aNa+svcraq6y9jLUXX/wWmXqJq+Epdh76nl/HtEs18iasusjDra58Xtuoqy4kVm"
    "lsBKELhwuMUBsu7CTu5iXwFyJdLGDLgK8fHJ0enR2eHI3xHpeUwZyFNIoeLoJmLu8PC6QM"
    "IguL5PFGvOtO423c/HlOqBg9isbVFXyz7XTsYpY03cMZ0nQPC9N0D9NpupVdWtmllV2asU"
    "uTYeIi2zQTTJ5in+qY9mRIu3qKdLvtUeYNoR0O4zQWs03zBSykUl8/U2FNUUk2lK4yFr1+"
    "zGWvAC8BPDREJyDLScf59a5zU2rHptlTkD8IwOKTxU21S2zuqc+rOtwmVEsXTiBQxd4eNr"
    "gi7YK4JO4oI1ts57rx/7SZdnnVuUirIRRwkeupLTgfuczVbCw+G3iCf2GWYQI2femO5p2Q"
    "Iv5qThafE6YMzwfjiisfu2oMmaC2ynkU9L0tacFJUSIjNTU9FLKq6TjYqx+vBPhm5+Hiqk"
    "U+3rYu23ftcBLGQRNdiUXxk/O3rcbVhrqPbyfR/0XP2Ex1NKNs2VW7mauejxU5mS93HBPp"
    "2kV+Yzqne4rbqE9sb4J8anotzDDBV1Rw4UvfI0DOlDnAB31MfOKHWUTLJBj73cVnlTAHNj"
    "QJshm1L5KGDz7dDxg+4MQ9Ml5HSOYwB4478jRgwcNS4RChAeoqb5d4kuhn8EnP9r0BMSl4"
    "g0OPuSqgBmCJK5+ghb8ZrDOMdf+NbQCIvKtbsUfEZj1FpK8fcgqE6TV5TrhCWpc9uVwphn"
    "0mjMKodFszPvJUlOqjB1Cl+lSpPm/EA6xSfVaP8YTOyGBcnuqT5KxSfdad6hMdRvPO4yRf"
    "NYvrnsVN8Wzekr6rAmPbHBjDdx7UclwaXV7qxfgRRfXOheqdC9ujrrJOx4suZ5a3ExvM5e"
    "Ygby+GNaW7kcY0GxN+fkML84U5T8V+7jfmRjdA2TSoglhPzLKdb4WsHx/PkO8EVIUZT7ou"
    "6Wrh1pgDxJB8OwE82N+fAUCgKnnL637m3Y5FL8wtDnIVvzD31eJaK/NtlhbBWuvx8vwvEM"
    "uawA=="
)
