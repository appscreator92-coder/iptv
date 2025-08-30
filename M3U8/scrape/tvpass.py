import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytz

base_url = "https://tvpass.org/playlist/m3u"

base_file = Path(__file__).parent / "tvpass.json"

TZ = pytz.timezone("America/New_York")

urls: dict[str, dict[str, str]] = {}

logos = {
    "MLB": "https://i.gyazo.com/ff3e375a48039d86d9b6216b213ad327.png",
    "NBA": "https://i.gyazo.com/29485b295d32782bbae31a0b35de0970.png",
    "NCAAF": "https://i.gyazo.com/ca63b40c86e757436de9d34d369b24f8.png",
    "NCAAB": "https://i.gyazo.com/ca63b40c86e757436de9d34d369b24f8.png",
    "NFL": "https://i.gyazo.com/8581d3d8cd6d902029e0daf9ca087842.png",
    "NHL": "https://i.gyazo.com/b634ca5b0d3f16f9863eca3b27568a10.png",
    "WNBA": "https://i.gyazo.com/f356a338044d1dfa9eed11979f8cf13f.png",
}


def cache_expired(t: float) -> bool:
    now = datetime.now(TZ)

    eleven = now.replace(hour=11, minute=0, second=0, microsecond=0)

    if now < eleven:
        eleven -= timedelta(days=1)

    return t < eleven.timestamp()


def load_cache() -> dict[str, str]:
    try:
        data = json.loads(base_file.read_text(encoding="utf-8"))

        ts = data.get("_timestamp", 0)

        return {} if cache_expired(ts) else data.get("urls", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(urls: dict[str, str]) -> None:
    payload = {"_timestamp": datetime.now(TZ).timestamp(), "urls": urls}

    base_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


async def fetch_m3u8(client: httpx.AsyncClient) -> list[str] | None:
    try:
        r = await client.get(base_url)
        r.raise_for_status()
    except Exception as e:
        print(f'Failed to fetch "{base_url}"\n{e}')

    return r.text.splitlines()


async def main(client: httpx.AsyncClient) -> None:
    if cached := load_cache():
        urls.update(cached)
        print(f"TVPass: Collected {len(urls)} live events from cache")
        return

    print(f'Scraping from "{base_url}"')

    if not (data := await fetch_m3u8(client)):
        return

    for i, line in enumerate(data):
        if line.startswith("#EXTINF"):
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
            group_title_match = re.search(r'group-title="([^"]*)"', line)

            tvg_id = tvg_id_match[1] if tvg_id_match else None
            tvg_name = tvg_name_match[1] if tvg_name_match else None
            sport = group_title_match[1].upper().strip() if group_title_match else None

            if tvg_id == "":
                url = data[i + 1]

                if tvg_name:
                    tvg_name = "(".join(tvg_name.split("(")[:-1]).strip()

                    logo = logos.get(
                        sport,
                        "https://i.gyazo.com/ec27417a9644ae517196494afa72d2b9.png",
                    )

                if url.endswith("/hd"):
                    parts = urlparse(url).path.strip("/").split("/")

                    link = f"http://origin.thetvapp.to/hls/{parts[1]}/mono.m3u8"

                    urls[f"[{sport}] {tvg_name} (SD)"] = {"logo": logo, "url": link}

    if urls:
        save_cache(urls)
        print(f"Cached {len(urls)} live events")
