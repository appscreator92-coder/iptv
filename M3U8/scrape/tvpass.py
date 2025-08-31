import json
import re
from datetime import datetime
from pathlib import Path

import httpx
import pytz

from .logger import get_logger

log = get_logger(__name__)

base_url = "https://tvpass.org/playlist/m3u"

base_file = Path(__file__).parent / "tvpass.json"

urls: dict[str, dict[str, str]] = {}

logos = {
    "MLB": "https://i.gyazo.com/0fe7865ef2f06c9507791b24f04dbca8.png",
    "NBA": "https://i.gyazo.com/773c23570f095a5d549c23b9401d83f4.png",
    "NCAAF": "https://i.gyazo.com/ca63b40c86e757436de9d34d369b24f8.png",
    "NCAAB": "https://i.gyazo.com/ca63b40c86e757436de9d34d369b24f8.png",
    "NFL": "https://i.gyazo.com/fb4956d7a2fe54a1bac54cd81e1b3f11.png",
    "NHL": "https://i.gyazo.com/526607d4e886d5ed1fecca4bff3115e2.png",
    "WNBA": "https://i.gyazo.com/02d665a5704118d195dbcd5fa20d5462.png",
}


def load_cache() -> dict[str, str]:
    TZ = pytz.timezone("America/New_York")

    try:
        data = json.loads(base_file.read_text(encoding="utf-8"))

        return {} if 8 <= datetime.now(TZ).hour <= 12 else data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def fetch_m3u8(client: httpx.AsyncClient) -> list[str] | None:
    try:
        r = await client.get(base_url)
        r.raise_for_status()
    except Exception as e:
        log.error(f'Failed to fetch "{base_url}"\n{e}')

    return r.text.splitlines()


async def main(client: httpx.AsyncClient) -> None:
    if cached := load_cache():
        urls.update(cached)
        log.info(f"TVPass: Collected {len(urls)} live events from cache")
        return

    log.info(f'Scraping from "{base_url}"')

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

                if url.endswith("/hd"):
                    urls[f"[{sport}] {tvg_name}"] = {
                        "url": f"http://origin.thetvapp.to/hls/{url.split('/')[-2]}/mono.m3u8",
                        "logo": logos.get(
                            sport,
                            "https://i.gyazo.com/ec27417a9644ae517196494afa72d2b9.png",
                        ),
                    }

    if urls:
        base_file.write_text(json.dumps(urls, indent=2), encoding="utf-8")

        log.info(f"Cached {len(urls)} live events")
