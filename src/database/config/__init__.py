# Copyright (c) NiceBots
# SPDX-License-Identifier: MIT

from collections import defaultdict
from logging import getLogger

import aerich
from tortoise import Tortoise

from src.config import config
from src.config.models import DbExtraApp, DbParams

logger = getLogger("bot").getChild("database")


def apply_params(uri: str, params: DbParams | None) -> str:
    if params is None:
        return uri

    first: bool = True
    for param, value in params.model_dump().items():
        if value is not None:
            uri += f"{'?' if first else '&'}{param}={value}"
            first = False
    return uri


app_url_mapping: dict[str, str] = {
    app_name: apply_params(app_config.url or config.db.url, app_config.params)
    for app_name, app_config in config.db.extra_apps.items()
}

url_apps_mapping: dict[str, list[str]] = defaultdict(list)

for app_name, app_url in app_url_mapping.items():
    url_apps_mapping[app_url].append(app_name)

app_connections_mapping: dict[str, str] = {}
connection_url_mapping: dict[str, str] = {}

i: int = 0

for url, apps in url_apps_mapping.items():
    connection_name = f"connection_{i}"
    connection_url_mapping[connection_name] = url
    for app in apps:
        app_connections_mapping[app] = connection_name
    i += 1  # noqa: SIM113 # Incompatible with .items()

app_connections_mapping["models"] = "default"
connection_url_mapping["default"] = apply_params(config.db.url, config.db.params)

config.db.extra_apps["models"] = DbExtraApp(
    models=["src.database.models", "aerich.models"],
)

TORTOISE_ORM = {
    "connections": connection_url_mapping,
    "apps": {
        app_name: {
            "models": app.models,
            "default_connection": app_connections_mapping[app_name],
        }
        for app_name, app in config.db.extra_apps.items()
    },
}


async def init() -> None:
    command = aerich.Command(
        TORTOISE_ORM,
        app="models",
        location="./src/database/migrations/",
    )
    await command.init()
    migrated = await command.upgrade(run_in_transaction=True)
    logger.success(f"Successfully migrated {migrated} migrations")  # pyright: ignore [reportAttributeAccessIssue]
    await Tortoise.init(config=TORTOISE_ORM)


async def shutdown() -> None:
    await Tortoise.close_connections()


__all__ = ["init", "shutdown"]
