# Copyright (c) 2025 Bryan Thoury
# SPDX-License-Identifier: MIT

import asyncio
import json
from pathlib import Path
from typing import Any


class WelcomeStorage:
    def __init__(self, path: str = "data/welcome.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def _read_all(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        txt = self.path.read_text(encoding="utf-8").strip()
        return json.loads(txt) if txt else {}

    async def _write_all(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def get(self, guild_id: int) -> dict[str, Any]:
        async with self._lock:
            data = await self._read_all()
            return data.get(str(guild_id), {})

    async def set(
        self,
        guild_id: int,
        *,
        channel_id: int | None = None,
        message: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        async with self._lock:
            data = await self._read_all()
            gid = str(guild_id)
            current: dict[str, Any] = data.get(gid, {})

            if channel_id is not None:
                current["channel_id"] = int(channel_id)
            if message is not None:
                current["message"] = str(message)
            if enabled is not None:
                current["enabled"] = bool(enabled)

            data[gid] = current
            await self._write_all(data)

    async def disable(self, guild_id: int) -> None:
        await self.set(guild_id, enabled=False)
