#!/usr/bin/env python3
from pathlib import Path

import httpx
from scrape import fstv, tvpass

m3u8_file = Path(__file__).parent / "TV.m3u8"

base_url = "https://s.id/ePwXT"

client = httpx.Client(
    timeout=5,
    follow_redirects=True,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    },
)


def vanilla_fetch() -> tuple[list[str], int]:
    print("Fetching base M3U8")

    try:
        r = client.get(base_url)
        r.raise_for_status()
    except Exception as e:
        raise SystemExit(f'Failed to fetch "{base_url}"\n{e}') from e

    d = r.text.splitlines()

    d.pop(0)

    last_chnl_number = int(r.text.split("tvg-chno=")[-1].split('"')[1])

    return d, last_chnl_number


def main() -> None:
    tvpass.main(client)

    fstv.main(client)

    base_m3u8, chnl_number = vanilla_fetch()

    additions = {**tvpass.urls, **fstv.urls}

    lines = []

    for event, url in sorted(additions.items()):
        chnl_number += 1
        lines.append(
            f'#EXTINF:-1 tvg-chno="{chnl_number}"'
            f' tvg-id="(N/A)" tvg-name="{event}"'
            ' tvg-logo="https://i.gyazo.com/ec27417a9644ae517196494afa72d2b9.png"'
            f' group-title="Live Events",{event}\n{url}\n'
        )

    m3u8_file.write_text(
        '#EXTM3U url-tvg="https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/EPG/TV.xml"\n'
        + "\n".join(base_m3u8)
        + "\n"
        + "".join(lines)
        + "\n",
        encoding="utf-8",
    )

    print(f"M3U8 saved to {m3u8_file.name}")


if __name__ == "__main__":
    main()
