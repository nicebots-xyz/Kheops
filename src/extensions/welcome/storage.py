import json
import asyncio
from pathlib import Path
from typing import Any, Dict


class WelcomeStorage:
    def __init__(self, path: str = "data/welcome.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def _read_all(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        txt = self.path.read_text(encoding="utf-8").strip()
        return json.loads(txt) if txt else {}

    async def _write_all(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def get(self, guild_id: int) -> Dict[str, Any]:
        async with self._lock:
            data = await self._read_all()
            return data.get(str(guild_id), {})

    async def set(self, guild_id: int, *, channel_id: int, message: str, enabled: bool = True) -> None:
        async with self._lock:
            data = await self._read_all()
            data[str(guild_id)] = {
                "enabled": enabled,
                "channel_id": int(channel_id),
                "message": str(message),
            }
            await self._write_all(data)

    async def disable(self, guild_id: int) -> None:
        async with self._lock:
            data = await self._read_all()
            current = data.get(str(guild_id), {})
            current["enabled"] = False
            data[str(guild_id)] = current
            await self._write_all(data)
