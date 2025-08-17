import json
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

base_url = "https://tvpass.org/playlist/m3u"
base_file = Path(__file__).parent / "tvpass.json"

urls: dict[str, str] = {}


def fetch_m3u8() -> list[str] | None:
    try:
        r = httpx.get(
            base_url,
            follow_redirects=True,
            timeout=5,
        )

        r.raise_for_status()

    except Exception as e:
        print(f'Failed to fetch "{base_url}"\n{e}')

        return

    return r.text.splitlines()


def main() -> None:
    print(f'Scraping from "{base_url}"')

    if not (data := fetch_m3u8()):
        return

    for i in range(len(data) - 1):
        if data[i].startswith("#EXTINF"):
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', data[i])
            tvg_name_match = re.search(r'tvg-name="([^"]*)"', data[i])

            tvg_id = tvg_id_match[1] if tvg_id_match else None
            tvg_name = tvg_name_match[1]

            if tvg_id == "":
                url = data[i + 1]

                tvg_name = tvg_name.split("(")[0].strip()

                if url.endswith("/sd"):

                    path_parts = urlparse(url).path.strip("/").split("/")

                    if len(path_parts) >= 2 and path_parts[-1] == "sd":
                        sport = "".join(x for x in path_parts[1] if x.isalpha()).upper()
                    else:
                        sport = "UNKNWN"

                    urls[f"[{sport}] {tvg_name}"] = url

    print(f"Collected {len(urls)} live events")

    if urls:
        base_file.write_text(json.dumps(urls, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
