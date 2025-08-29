import asyncio
import json
from typing import List

from playwright.async_api import async_playwright


URL = (
    "https://vfscigaming.aitcloud.de/vflmshop/retail/index?clientid=4997&lang=zh&style=scigamingcdn&screen=betradar_vflm_one_screen&channel=7"
)
OUT = "feeds.jsonl"


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        async def handle_request(route, request):
            await route.continue_()

        async def handle_response(response):
            url = response.url
            # capture likely widget feed calls
            if "/ls/feeds/" in url or "/gismo" in url or "/gismop" in url:
                try:
                    txt = await response.text()
                except Exception:
                    return
                rec = {"url": url, "status": response.status, "body": txt}
                with open(OUT, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        await context.route("**/*", handle_request)
        page.on("response", handle_response)

        await page.goto(URL, wait_until="load")
        # hagyjuk futni egy ideig, hogy a widgetek betöltsenek és kérdéseket indítsanak
        await asyncio.sleep(30)

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())

