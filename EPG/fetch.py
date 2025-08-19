#!/usr/bin/env python3
import gzip
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

epg_file = Path(__file__).parent / "TV.xml"
epg_urls = [
    "https://epgshare01.online/epgshare01/epg_ripper_US1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US_LOCALS2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_FANDUEL1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_CA1.xml.gz",
]

client = httpx.Client(
    timeout=5,
    follow_redirects=True,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    },
)


def fetch_tvg_ids() -> dict[str, str]:
    try:
        r = client.get("https://s.id/4dqiO")
        r.raise_for_status()
    except Exception as e:
        raise SystemExit(f"Failed to fetch TVG IDs\n{e}") from e

    return r.json()


def fetch_xml(url: str) -> ET.Element:
    try:
        r = client.get(url)
        r.raise_for_status()
    except Exception as e:
        raise SystemExit(f'Failed to fetch "{url}"\n{e}') from e

    try:
        decompressed_data = gzip.decompress(r.content)

        return ET.fromstring(decompressed_data)

    except Exception as e:
        raise SystemExit(f'Failed to decompress and parse XML from "{url}"\n{e}') from e


def main() -> None:
    tvg_ids = fetch_tvg_ids()

    root = ET.Element("tv")

    for url in epg_urls:
        epg_data = fetch_xml(url)

        for channel in epg_data.findall("channel"):
            if (channel_id := channel.get("id")) in tvg_ids:
                for icon_tag in channel.findall("icon"):
                    icon_tag.set("src", tvg_ids[channel_id])

                if (url_tag := channel.find("url")) is not None:
                    channel.remove(url_tag)

                root.append(channel)

        for program in epg_data.findall("programme"):
            tvg_id = program.get("channel")

            if tvg_id in tvg_ids:
                if (title_text := program.find("title").text) in [
                    "NHL Hockey",
                    "Live: NFL Football",
                ] and (subtitle := program.find("sub-title")) is not None:

                    program.find("title").text = f"{title_text} {subtitle.text}"

                root.append(program)

    tree = ET.ElementTree(root)

    tree.write(epg_file, encoding="utf-8", xml_declaration=True)

    print(f"EPG saved to {epg_file.name}")


if __name__ == "__main__":
    main()
