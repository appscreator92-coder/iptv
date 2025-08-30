#!/usr/bin/env python3
import asyncio
from pathlib import Path

import httpx
from scrape import fstv, logger, tvpass

log = logger.get_logger(__name__)

base_url = "https://s.id/ePwXT"

m3u8_file = Path(__file__).parent / "TV.m3u8"

client = httpx.AsyncClient(
    timeout=5,
    follow_redirects=True,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    },
)


async def vanilla_fetch() -> tuple[list[str], int]:
    log.info("Fetching base M3U8")

    try:
        r = await client.get(base_url)
        r.raise_for_status()
    except Exception as e:
        log.error(f'Failed to fetch "{base_url}"\n{e}')
        raise SystemExit(e) from e

    d = r.text.splitlines()[1:]

    last_chnl_number = int(r.text.split("tvg-chno=")[-1].split('"')[1])

    return d, last_chnl_number


async def main() -> None:
    await tvpass.main(client)

    await fstv.main(client)

    base_m3u8, chnl_number = await vanilla_fetch()

    additions = tvpass.urls | fstv.urls

    lines = [
        f'#EXTINF:-1 tvg-chno="{chnl_number}" tvg-id="(N/A)" tvg-name="{event}" tvg-logo="{info["logo"]}" group-title="Live Events",{event}\n{info["url"]}'
        for chnl_number, (event, info) in enumerate(
            sorted(additions.items()),
            start=chnl_number + 1,
        )
    ]

    m3u8_file.write_text(
        '#EXTM3U url-tvg="https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/EPG/TV.xml"\n'
        + "\n".join(base_m3u8)
        + "\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )

    log.info(f"M3U8 saved to {m3u8_file.name}")


if __name__ == "__main__":
    asyncio.run(main())
