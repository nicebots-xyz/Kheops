# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 Communauté Les Frères Poulain, NiceBots.xyz

from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "absence" ADD "kind" VARCHAR(7) NOT NULL DEFAULT 'full';
        ALTER TABLE "absence" ADD "availability_note" VARCHAR(300);
        COMMENT ON COLUMN "absence"."kind" IS 'FULL: full\nPARTIAL: partial';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "absence" DROP COLUMN "kind";
        ALTER TABLE "absence" DROP COLUMN "availability_note";"""


MODELS_STATE = (
    "eJztXetvIjkS/1es/pSRslGAvDY6nUQC2eE2j7k89u52Muo1tAlWGpvpdieLRvO/X9n9op"
    "/QBMIjng8ZsKvc7V/Z5SpX2fwwhtwitrvX7LqE9Yhxin4YDA/lh3TVLjLwaBRXyAKBu7ai"
    "xRNEXVc4uCeguI9tl0CRRdyeQ0eCcgalzLNtWch7QEjZU1zkMfrdI6bgT0QMiAMVX79BMW"
    "UW+Zu48utX48mjtmVSSz5qSIZd4sgv3yTd6NnsU2JbiV74lKrcFOORKnt46LQuFKV8j67Z"
    "47Y3ZDH1aCwGnEXknketPckj654IIw4WxJron3z9AImwyO8KFAjHI1EfrLjAIn3s2RIl4x"
    "99j/UkOEg9Sf45+KdRAbceZxJzyoQE6cdPv1dxn1WpIR91/rl5u9M4+qR6yV3x5KhKhYjx"
    "UzFigX1WBfjEcIjAzuB5Rp86TOQjmmBLAQsvPA+kYUGMaTzQQlBDsOZDEF4J/vvl13q90T"
    "iu7zeOTg4Pjo8PT/ZPgFa9VLbquAT2s85vnet72VcOU8OfMrJAIh4j7ArsCBMEQLIQt6A0"
    "H+AkVwphWSzokOyF9euHdQlsreZ9O4URYVZlhCZ5th0fh2AX2s+gcz7ATj46MUcKG3iJZS"
    "FivEG7GUP8t2kT9iQG8PVwf78EoD+at0rjAdWn5Oy7Dqrqfl0SxGd493wI28wbKhg78E44"
    "WPEScIa87whmHxrIAmpcPFxeAj1UPrIvzdv7ThO+jkBZUOyTV4S6TMGFQB8XwnycBhm/YA"
    "r9pjYVY5PxvCldPGhzmeeCPFiO33NxSaDamGkAN0oGcCM7gHswqaHHZndceb3OsOo1u2zN"
    "xoxxsN6I2RvAR2JXxruggblQX8FYXi3oQ+K6+InMD3qyAQ16Ceg9udzZNqgGLPKtL2lIFS"
    "iVFG+ZFSY/rCXsJQjed67ad/fNqy/KK3Xd73Zonsmauiodp0p3jlIaPWoE/adz/xnJr+jP"
    "m+t22leL6O7/NOQ7YU9wWANfTWxNdjssDotyF4g5RJngXIAgV7FUQB+sG2aPg3G0IZINhn"
    "ypYL2RNadgk5xasCsVbPDysVwnt71mX+cmubQdl17d5J5h/zl3s0sBl8X6gjuEPrHfyTjj"
    "BKbgDTZPfwvbWT+cf4aDJSyNB6KDX6Od1MQYgg5Ct4jwvbPm3Xmz1TYUjl3ce37FjmUmAJ"
    "U1vM5TJRFttmpYH6ZLMAMDzQq6IV86uS99R4SAbvryzt+6jkh2Z9jCdieJl7mVrXesl71j"
    "jW2bv8KK5nBbWvhuFtZ/3d1cF3gIObwpkB8Y9PKrRXtiF9nUFd+WtsETw92FyQjD092TD1"
    "wS4hKUxKIYbjXsXDX/m96FOL+8OUuLRjZwpv3k1btsII8RvAeFXocDuRroBQ1o0EtAXxdL"
    "bboa3xR0M3ZaFYNjqk13w8g9hz/LtuiWLY8l2XNvstHOfV19zdUTMvbZZHWpbRbo/HCjX9"
    "tlG22XWdTtcae6jkzyaS1ZvAYRJvubBy+HVRyzojh5xJUCtwtsy7JuI8AXPULPbm4uE3bs"
    "WScF3PXD1Vn7dqemBjEQUVGAZ587YHnCCCd5geFSUNOs74hsVd24EmjhoYKwnN3K4uDvBM"
    "v7RdkXGfOt7dcPZgj6SrLCqK9fmcRyQLBFnCpQxhwbimT9ZBYg6yfFOMq69GwHO6MSjDGH"
    "hjFehF6IM85HcXoaTcS8YkCNz2btFA3M2iP7bB7JT0fyU62uCuuPrCXrLVnfMo/lp2NjDg"
    "HMog6KdUFGEejw3lZEgXR4b0sFq17+Tdsai/PRW9wZEs8xcvzzsGq3zDe3Joim+eVG0CJS"
    "7eylNWWq+pE9slsyUrazcBFGnkscRBkCzx1J77KLXaKomkI47qmxq/177d9vq3+/JurC3/"
    "/MURbRxmixqoh2YKcrigc51Qu0xERdNRVBu54g7iP7Jfr3yBD8oxbaAYF+OkUtfwj6zXRa"
    "e3593yHEBMvIovCMgLI55B4TiPdVLQpr5XMV8wC7ATe83ZB6w+IGAoL8Npag1Mrm4KxzL5"
    "hGH2PqZZVdhck4EQMNMgxyJBJwXvx+S2ysgMhKIXseb/0stKIgRPqcU79vBgfDVFiRg7fn"
    "UOut0NzJhq9Uu7fQ7E3Q6hZApbKUF4OOaqr9QtY1/6sCLmrsfPe4wIuARg6Zf8vGNh6XF0"
    "57xHRB1PCMRUDzh2zwzm9vw9CpZAtldLU5mQ6WD2IYP55Zc0+mo61dzkSFUQZ/hbtQgNRY"
    "u5PNbiZGFU3pouUqx7guWdmKzW0lJn+ZlZqSTzJNNcC/UCbtaZ8dDbhtASTIlfuy2EZK6S"
    "LZKpirXFmsnBH4HwsEL2TTqHyYtd8X23SOcfw19jRSVwTofYB33AfQNwYsPcFvrqS+Nyby"
    "fRh01yWTb5vw1WcuNvnMRdaFLLZVkn7mVCtFkZOI/B0uEUqaB7uJ2Ke+T0hbBxupXxNZAH"
    "MetVjACYuPg/GHzrTYkAB82O3S1Apt7WlrT1t7GWsv3hUvMvUS++ZT7Dzpe36PaBdq5E1Y"
    "daGHq7d83tuo0xsSyzQ2/LjOkDKZxmA6MJOok3fKoxDp4gY2DPh67eD44KRxdBDhHZWUwZ"
    "yFNAytzoNmLu+HBZJbBTf4TU/2DnlXnevdvP7fKcJs/Mia8upEbM91T2JjhlzuRvFtfulc"
    "bm2XartU26UZuzQZJi6yTTPB5Cn2qYpp6ytgtsce1TdgrOLakRF3xNw3veSya8BLAA9vMY"
    "0hq3TXUQG7vu5o/uuOfEdrTnnkMmtpzC8NuYI/E8vsATZP3BlXFUgRv5bJ/DIhwnQ9MK6o"
    "8OSrmiPCsC1yzgtf2BwXrBQlbaRE05eNLEsctb364VKAb908nF220Zfb9nnnrhMIIQqaqE"
    "pZFF+vcNtuXq6p+7g9p0HedBBLX0e1wuuosrnsRX5jOuF9ituoVmx3gnxqei1IGMl7TCjz"
    "uOciICeiN5CnwXryWBixkGoTydjvrjzQJnNgA5Mgm1H7ptbk6bj7AZGn4KiLonEkyYZkCM"
    "sdeh0Q/0Rd0EWkfnPI3UUuR+qiBtS3PXeAehi8wZFLHOFTA7DI4a/whL8IjDMZ6/5LPgNA"
    "pF31FHuMbNIXiHvqJJzfmBqTp4gKSeuQV4cKQeQ7I4KhV+pZM56LK0r1UR3QqT461WdLPE"
    "Cd6vNOP882V6pPklOn+qw61SdcjKrKcZJPS3HVUlwXz2ab9J0OjG1yYExejGHkuDSqvNSL"
    "8UIKfTGHvphjc9RV1ul40+bM4mZikzi0N8ibi0FN6WzEMc3ahJ+3aGC+Meep2M99IU64A5"
    "RNgyqI9cQsm3l1aP3wcIZ8J6AqzHhSdalfC4GpUQHEgHwzAazN9AOwtZIfgK3l/ABs0a3K"
    "xUGu4luV3y2utTTfZmERrJUuLz//Dy0Vpu8="
)
