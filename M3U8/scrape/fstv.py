import asyncio
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

urls: dict[str, str] = {}

mirrors = [
    "https://fstv.online",
    "https://fstv.space",
    "https://fstv.zip",
    "https://fstv.us",
]


async def check_status(client: httpx.AsyncClient, url: str) -> bool:
    try:
        r = await client.get(url)
        r.raise_for_status()
    except Exception:
        return False

    return r.status_code == 200


async def get_base(client: httpx.AsyncClient) -> str:
    tasks = [check_status(client, link) for link in mirrors]
    results = await asyncio.gather(*tasks)

    return [url for url, ok in zip(mirrors, results) if ok][0]


async def get_hrefs(client: httpx.AsyncClient, base_url: str) -> list[tuple[str, str]]:
    print(f'Scraping from "{base_url}"')

    try:
        r = await client.get(base_url)
        r.raise_for_status()
    except Exception as e:
        print(f'Failed to fetch "{base_url}"\n{e}')

        return []

    soup = HTMLParser(r.text)

    events = {}

    for wrpr in soup.css("div.fixtures-live-wrapper"):
        for games in wrpr.css(".match-table-item"):

            league_name = games.css_first(".league-info a.league-name")

            league_match = games.css_first(".common-table-row a[href*='/match/']")

            if league_name and league_match:
                full_text = league_name.text(strip=True)

                if "]" in full_text:
                    event_name = full_text.split("]", 1)[1].strip()
                else:
                    event_name = full_text

                events[event_name] = urljoin(
                    base_url, league_match.attributes.get("href")
                )

    return events.items()


async def fetch_m3u8(client: httpx.AsyncClient, url: str) -> tuple[str, list[str]]:
    try:
        r = await client.get(url)
        r.raise_for_status()
    except Exception as e:
        print(f'Failed to fetch "{url}"\n{e}')

        return []

    soup = HTMLParser(r.text)

    if category_links := soup.css(".common-list-category .category-item a"):
        match_name = category_links[-1].text(strip=True)
    else:
        match_name = None

    if not match_name or match_name.lower() == "vs":
        if og_title := soup.css_first("meta[property='og:title']"):
            match_name = (
                og_title.attributes.get("content", "").split(" start on")[0].strip()
            )

    btns = soup.css("button.btn-server")

    return match_name, [
        btn.attributes.get("data-link") for btn in btns if "data-link" in btn.attributes
    ]


async def main(client: httpx.AsyncClient) -> None:
    if not (base_url := await get_base(client)):
        print("No working FSTV mirrors")
        return

    events = await get_hrefs(client, base_url)

    tasks = [fetch_m3u8(client, href) for _, href in events if href]
    results = await asyncio.gather(*tasks)

    for (event, _), (match_name, m3u8_urls) in zip(events, results):
        if not m3u8_urls:
            continue

        for i, link in enumerate(m3u8_urls, start=1):
            key = (
                f"[{event}] {match_name} (S{i})" if match_name else f"[{event}] (S{i})"
            )

            urls[key] = link

    print(f"Collected {len(urls)} live events")
