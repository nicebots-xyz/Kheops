# SPDX-License-Identifier: MIT
# Copyright: 2024-2026 NiceBots.xyz

import nodriver as uc
from bs4 import BeautifulSoup

from .Listing import Listing


class WumpusStore(Listing):
    name: str = "Wumpus.store"

    def __init__(self, browser: uc.Browser, application_id: int) -> None:
        super().__init__(browser)
        self.application_id = application_id

    async def fetch_raw_description(self) -> str:
        url = f"https://wumpus.store/bot/{self.application_id}"
        page = await self.browser.get(url)
        description = await page.select(".css-2yutdr")
        html = await description.get_html()
        soup = BeautifulSoup(html, "html.parser")
        outer = soup.select_one("div")
        inner = outer.select_one("div") if outer is not None else None
        if inner is not None:
            inner.decompose()
        return self.normalize_soup(soup)
