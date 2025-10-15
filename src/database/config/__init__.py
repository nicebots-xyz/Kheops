# Copyright (c) NiceBots
# SPDX-License-Identifier: MIT

from collections import defaultdict
from logging import getLogger

import aerich
from tortoise import Tortoise

from src.config import config
from src.config.models import DbParams

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


def get_app_url_mapping() -> dict[str, str]:
    return {
        app_name: apply_params(app_config.url or config.db.url, app_config.params)
        for app_name, app_config in config.db.extra_apps.items()
    }


def get_url_apps_mapping() -> dict[str, list[str]]:
    app_url_mapping: dict[str, str] = get_app_url_mapping()
    mapping: dict[str, list[str]] = defaultdict(list)

    for app_name, app_url in app_url_mapping.items():
        mapping[app_url].append(app_name)

    return mapping


def parse_url_apps_mapping(url_apps_mapping: dict[str, list[str]]) -> tuple[dict[str, str], dict[str, str]]:
    app_connection: dict[str, str] = {}
    connection_url: dict[str, str] = {}

    for i, (url, apps) in enumerate(url_apps_mapping.items()):
        connection_name = f"connection_{i}"
        connection_url[connection_name] = url
        for app in apps:
            app_connection[app] = connection_name

    app_connection["models"] = "default"
    connection_url["default"] = apply_params(config.db.url, config.db.params)

    return app_connection, connection_url


APP_CONNECTION_MAPPING: dict[str, str]
CONNECTION_URL_MAPPING: dict[str, str]

APP_CONNECTION_MAPPING, CONNECTION_URL_MAPPING = parse_url_apps_mapping(get_url_apps_mapping())  # pyright: ignore[reportConstantRedefinition]


def get_apps() -> dict[str, dict[str, list[str] | str]]:
    apps = {
        app_name: {
            "models": app.models,
            "default_connection": APP_CONNECTION_MAPPING[app_name],
        }
        for app_name, app in config.db.extra_apps.items()
    }
    apps["models"] = {
        "models": ["src.database.models", "aerich.models"],
        "default_connection": "default",
    }
    return apps


TORTOISE_ORM = {
    "connections": CONNECTION_URL_MAPPING,
    "apps": get_apps(),
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


__all__ = ["APP_CONNECTION_MAPPING", "init", "shutdown"]
