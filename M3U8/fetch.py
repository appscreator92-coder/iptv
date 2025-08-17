#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

import httpx
import pytz
from scrape import fstv, tvpass

m3u8_file = Path(__file__).parent / "TV.m3u8"

base = "http://m3u4u.com/m3u/d5k2nvp8w2t3w2k1n984"

current_hour = datetime.now(pytz.timezone("America/New_York")).hour


def vanilla_fetch() -> tuple[list[str], int]:
    print("Fetching base M3U8")

    try:
        r = httpx.get(
            base,
            follow_redirects=True,
            timeout=5,
        )

        r.raise_for_status()
    except Exception as e:
        raise SystemExit(f'Failed to fetch "{base}"\n{e}') from e

    d = r.text.splitlines()

    d.pop(0)

    last_chnl_number = int(r.text.split("tvg-chno=")[-1].split('"')[1])

    return d, last_chnl_number


def main() -> None:
    if current_hour <= 11:
        tvpass.main()
    else:
        try:
            tvpass.urls = json.loads(tvpass.base_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    fstv.main()

    base_m3u8, chnl_number = vanilla_fetch()

    m3u8_file.write_text(
        '#EXTM3U url-tvg="https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/EPG/TV.xml"\n'
        + "\n".join(base_m3u8)
        + "\n",
        encoding="utf-8",
    )

    additions = tvpass.urls | fstv.urls

    for event, url in additions.items():
        chnl_number += 1

        with m3u8_file.open("a", encoding="utf-8") as f:
            f.write(f'#EXTINF:-1 tvg-chno="{chnl_number}"')
            f.write(f' tvg-id="(N/A)" tvg-name="{event}"')
            f.write(
                ' tvg-logo="https://i.gyazo.com/ec27417a9644ae517196494afa72d2b9.png"'
            )
            f.write(' group-title="Live Events"')
            f.write(f",{event}\n{url}\n")

    print(f"M3U8 saved to {m3u8_file.name}")


if __name__ == "__main__":
    main()
