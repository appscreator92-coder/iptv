#!/usr/bin/env python3
import asyncio
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import BrowserContext, Request, async_playwright

from .logger import get_logger
from .tvpass import logos

base_url = "https://livetv.sx/enx/"

log = get_logger(__name__)

tvp_sports = set(logos.keys())

urls: dict[str, str] = {}


async def safe_process_event(fn, timeout_sec=20) -> Any | None:
    try:
        return await asyncio.wait_for(fn(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        log.warning(f"Timed out after {timeout_sec}s, skipping event")


async def process_event(
    ev: dict[str, str],
    context: BrowserContext,
    max_wait_ms=15_000,
) -> str | None:
    ev_page = await context.new_page()

    captured: list[str] = []

    got_one = asyncio.Event()

    def capture_req(req: Request) -> None:
        if (
            ".m3u8" in req.url
            and "amazonaws" not in req.url
            and "knitcdn" not in req.url
            and not captured
        ):
            captured.append(req.url)

            got_one.set()

    popup = None

    try:
        await ev_page.goto(ev["href"], wait_until="domcontentloaded", timeout=30_000)

        btn = await ev_page.query_selector(".lnkhdr > tbody > tr > td:nth-child(2)")

        if btn:
            try:
                await btn.click()

                await ev_page.wait_for_timeout(500)
            except Exception as e:
                log.debug(f"Failed to click Browser Links tab: {e}")
        else:
            log.warning("Browser Links tab not found")

        link_img = await ev_page.query_selector(
            "tr:nth-child(2) > td:nth-child(1) td:nth-child(6) img"
        )

        if not link_img:
            log.warning("No browser link to click.")

        ev_page.on("request", capture_req)

        try:
            async with ev_page.expect_popup(timeout=5_000) as popup_info:
                try:
                    await link_img.click()
                except Exception as e:
                    log.debug(
                        f"Click failed (popup might have already been opened): {e}"
                    )

            popup = await popup_info.value

            popup.on("request", capture_req)
        except Exception:

            try:
                await link_img.click()
            except Exception as e:
                log.debug(f"Fallback click failed: {e}")

        wait_task = asyncio.create_task(got_one.wait())

        try:
            await asyncio.wait_for(wait_task, timeout=max_wait_ms / 1000)

        except asyncio.TimeoutError:
            log.warning("Timed out waiting for m3u8.")

        finally:
            if not wait_task.done():
                wait_task.cancel()

                try:
                    await wait_task
                except asyncio.CancelledError:
                    pass

        ev_page.remove_listener("request", capture_req)

        if popup:
            popup.remove_listener("request", capture_req)

            await popup.close()

        await ev_page.close()

        if captured:
            return captured[-1]

        log.warning("No m3u8 captured in popup or inline playback.")

    except Exception as e:
        log.error(f"Error processing {ev['name']}: {e}")

        try:
            ev_page.remove_listener("request", capture_req)

            if popup:
                popup.remove_listener("request", capture_req)

                await popup.close()

            await ev_page.close()
        except Exception:
            pass


async def main() -> None:
    log.info(f'Scraping from "{base_url}"')

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)

        context = await browser.new_context()

        page = await context.new_page()

        await page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)

        rows = await page.query_selector_all("#upcoming table tr")

        events = []

        seen_hrefs = set()

        for row in rows:
            img = await row.query_selector("img")

            league = (await img.get_attribute("alt") or "").strip() if img else ""

            live_anchor = None

            for a in await row.query_selector_all("a.live"):
                txt = (await a.text_content() or "").strip()

                if txt:
                    live_anchor = a
                    break

            if live_anchor:
                href = await live_anchor.get_attribute("href")

                full_url = urljoin(base_url, href)

                if full_url in seen_hrefs:
                    continue

                seen_hrefs.add(full_url)

                text = (await live_anchor.text_content() or "").strip()

                events.append({"name": text, "href": full_url, "league": league})

        for ev in events:
            if (
                sport := ev["league"].split(".")[-1].strip()
            ) in tvp_sports:  # already in tvpass
                continue

            url = await safe_process_event(lambda: process_event(ev, context))

            if url:
                urls[f"[{sport}] {ev['name']}"] = {
                    "url": url,
                    "logo": logos.get(
                        sport,
                        "https://i.gyazo.com/ec27417a9644ae517196494afa72d2b9.png",
                    ),
                }

        await browser.close()

        log.info(f"Collected {len(urls)} live events")
