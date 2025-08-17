from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

urls: dict[str, str] = {}

mirrors = {"https://fstv.online", "https://fstv.space", "https://fstv.zip"}


def check_status(l: str) -> bool:
    try:
        r = httpx.get(l)
        r.raise_for_status()
    except Exception:
        return False

    return r.status_code == 200


def get_base() -> str:
    for url in filter(check_status, mirrors):
        return url


def get_hrefs(base_url: str) -> list[tuple[str, str]] | tuple[None, None]:
    print(f'Scraping from "{base_url}"')

    try:
        r = httpx.get(
            base_url,
            timeout=5,
        )

        r.raise_for_status()
    except Exception as e:
        print(f'Failed to fetch "{base_url}"\n{e}')

        return None, None

    soup = BeautifulSoup(r.text, "lxml")

    events = {}

    for wrpr in soup.find_all("div", class_="fixtures-live-wrapper"):
        for games in wrpr.select(".match-table-item"):

            league_name = games.select_one(".league-info a.league-name")

            league_match = games.select_one(".common-table-row a[href*='/match/']")

            if league_name and league_match:
                full_text = league_name.get_text(strip=True)

                if "]" in full_text:
                    event_name = full_text.split("]", 1)[1].strip()
                else:
                    event_name = full_text

                events[event_name] = urljoin(base_url, league_match["href"])

    return events.items()


def fetch_m3u8(url: str) -> tuple[str, list[str]] | tuple[None, None]:
    try:
        r = httpx.get(
            url,
            timeout=5,
        )

        r.raise_for_status()
    except Exception as e:
        print(f'Failed to fetch "{url}"\n{e}')

        return None, None

    soup = BeautifulSoup(r.text, "lxml")

    if category_links := soup.select(".common-list-category .category-item a"):
        match_name = category_links[-1].get_text(strip=True)
    else:
        match_name = None

    if not match_name or match_name.lower() == "vs":
        if og_title := soup.find("meta", property="og:title"):
            match_name = og_title["content"].split(" start on")[0].strip()

    btns = soup.select("button.btn-server")

    return match_name, [btn["data-link"] for btn in btns if btn.has_attr("data-link")]


def main() -> None:
    for event, href in get_hrefs(get_base()):

        if not href:
            return

        match_name, m3u8_urls = fetch_m3u8(href)

        if not m3u8_urls:
            return

        for i, link in enumerate(m3u8_urls, start=1):
            key = (
                f"[{event}] (S{i})"
                if not match_name
                else f"[{event}] {match_name} (S{i})"
            )

            urls[key] = link

    print(f"Collected {len(urls)} live events")


if __name__ == "__main__":
    main()
