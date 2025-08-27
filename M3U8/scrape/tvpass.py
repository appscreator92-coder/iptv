import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytz

base_url = "https://tvpass.org/playlist/m3u"
base_file = Path(__file__).parent / "tvpass.json"

urls: dict[str, str] = {}

TZ = pytz.timezone("America/New_York")


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

    for i, line in enumerate(data[:-1]):
        if line.startswith("#EXTINF"):
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)

            tvg_id = tvg_id_match[1] if tvg_id_match else None
            tvg_name = tvg_name_match[1] if tvg_name_match else None

            if tvg_id == "":
                url = data[i + 1]

                if tvg_name:
                    tvg_name = tvg_name.split("(")[0].strip()

                if url.endswith("/sd"):
                    path_parts = urlparse(url).path.strip("/").split("/")

                    if len(path_parts) >= 2 and path_parts[-1] == "sd":
                        sport = "".join(x for x in path_parts[1] if x.isalpha()).upper()
                    else:
                        sport = "UNKNWN"

                    urls[f"[{sport}] {tvg_name}"] = url

    if urls:
        save_cache(urls)
        print(f"Cached {len(urls)} live events")
