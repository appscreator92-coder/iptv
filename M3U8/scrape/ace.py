import asyncio
import re
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser, Node

from .fstv import get_base
from .logger import get_logger
from .tvpass import logos

log = get_logger(__name__)

urls: dict[str, dict[str, str]] = {}

mirrors = [
    "https://aceztrims.pages.dev/",
    "https://acestrlms.pages.dev/",
]


def is_valid_href(a: Node) -> bool:
    href = a.attributes.get("href", "")
    return href.startswith("/") and href != "/news/"


async def get_schedule(client: httpx.AsyncClient, base_url: str) -> list[dict]:
    log.info(f'Scraping from "{base_url}"')

    try:
        r = await client.get(base_url)
        r.raise_for_status()
    except Exception as e:
        log.error(f'Failed to fetch "{base_url}": {e}')
        return []

    html = re.sub(r"<!--.*?-->", "", r.text, flags=re.DOTALL)

    tree = HTMLParser(html)

    events = []

    for a in filter(is_valid_href, tree.css("a[href]")):
        href = a.attributes.get("href", "")

        title_text = a.text(strip=True)

        after_time = (
            title_text.split("//", 1)[1].strip() if "//" in title_text else title_text
        )

        if " - " in after_time:
            sport, event_name = [x.strip() for x in after_time.split(" - ", 1)]
        else:
            sport, event_name = "", after_time

        events.append(
            {"sport": sport, "event": event_name, "href": urljoin(base_url, href)}
        )

    return events


async def get_m3u8_links(client: httpx.AsyncClient, url: str) -> list[str]:
    try:
        r = await client.get(url)
        r.raise_for_status()
    except Exception as e:
        log.error(f'Failed to fetch "{url}": {e}')
        return []

    html = re.sub(r"<!--.*?-->", "", r.text, flags=re.DOTALL)

    tree = HTMLParser(html)

    m3u8_links = []

    for btn in tree.css("button[onclick]"):
        onclick = btn.attributes.get("onclick", "")

        if match := re.search(r"src\s*=\s*['\"](.*?)['\"]", onclick):
            link = match[1]

            if ".m3u8" in link:
                m3u8_links.append(link)

    if iframe := tree.css_first("iframe#iframe"):
        src = iframe.attributes.get("src", "")

        if ".m3u8" in src and src not in m3u8_links:
            m3u8_links.insert(
                0,
                src.split("cors.ricohspaces.app/")[-1],
            )

    return m3u8_links


async def main(client: httpx.AsyncClient) -> None:
    if not (base_url := await get_base(client, mirrors)):
        log.warning("No working ace mirrors")
        return

    schedule = await get_schedule(client, base_url)

    tasks = [get_m3u8_links(client, item["href"]) for item in schedule]

    results = await asyncio.gather(*tasks)

    for item, m3u8_urls in zip(schedule, results):
        if not m3u8_urls:
            continue

        for i, link in enumerate(m3u8_urls, start=1):
            sport, event = item["sport"], item["event"]

            urls[f"[{sport}] {event} (S{i})"] = {
                "url": link,
                "logo": logos.get(
                    sport,
                    "https://i.gyazo.com/ec27417a9644ae517196494afa72d2b9.png",
                ),
            }

    log.info(f"Collected {len(urls)} events")


# add caching
