import re
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from playwright.sync_api import sync_playwright


MEMORIA_PAGES = {
    "dbz": "https://www.memoriadatv.com/dragon-ball-z-1989-1996-dual-audio-bluray-1080p/",
    "db": "https://www.memoriadatv.com/dragon-ball-1986-1989-dual-audio-bluray-1080p/",
}


WORKER_BASE = "https://selecta-vision-proxy.edersonff.workers.dev"


@dataclass
class Episode:
    series_key: str
    number: int
    filename: str
    drime_hash: str
    stream_uuid: str
    hls_url: str


def get_drime_cookies() -> tuple[str, str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://dri.me/", wait_until="networkidle")
        page.wait_for_timeout(2000)

        cookies = context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        xsrf = ""
        for c in cookies:
            if c["name"] == "XSRF-TOKEN":
                xsrf = c["value"]
                break

        browser.close()
        return cookie_str, xsrf


def get_drime_hashes_from_memoria(series_key: str) -> List[str]:
    url = MEMORIA_PAGES.get(series_key)
    if not url:
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")

        # Find download link
        dl_href = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a'));
            const link = links.find(a => a.href.includes('/baixar/'));
            return link ? link.href : null;
        }""")

        if not dl_href:
            browser.close()
            return []

        page.goto(dl_href, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Get all Drime links
        hashes = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a'));
            return links
                .filter(a => a.href.includes('dri.me/'))
                .map(a => {
                    const match = a.href.match(/dri\\.me\\/([a-zA-Z0-9]+)/);
                    return match ? match[1] : null;
                })
                .filter(Boolean);
        }""")

        browser.close()
        return list(dict.fromkeys(hashes))


def fetch_drime_files(drime_hash: str, cookies: str, xsrf: str) -> List[dict]:
    api_url = (
        f"https://app.drime.cloud/api/v1/shareable-links/{drime_hash}?withEntries=true"
    )

    headers = {
        "accept": "application/json",
        "cookie": cookies,
        "x-xsrf-token": xsrf,
    }

    resp = requests.get(api_url, headers=headers)
    if resp.status_code != 200:
        return []

    data = resp.json()
    return data.get("folderChildren", {}).get("data", [])


def parse_episode_number(filename: str, series_key: str) -> Optional[int]:
    patterns = {
        "dbz": [r"DBZ[_.\s-]?(\d+)", r"DBZ\.(\d+)"],
        "db": [r"DB[_.\s-]?(\d+)", r"DB\.(\d+)"],
    }

    for pattern in patterns.get(series_key, [r"(\d+)"]):
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1))

    # Fallback: look for any 3-digit number
    match = re.search(r"\.(\d{3})\.", filename)
    if match:
        return int(match.group(1))

    return None


def scrape_series(series_key: str, cookies: str, xsrf: str) -> List[Episode]:
    hashes = get_drime_hashes_from_memoria(series_key)
    print(f"[{series_key}] Found {len(hashes)} Drime folders")

    episodes = []
    for drime_hash in hashes:
        files = fetch_drime_files(drime_hash, cookies, xsrf)

        for f in files:
            name = f.get("name", "")
            ep_num = parse_episode_number(name, series_key)

            if not ep_num:
                continue

            thumbnail = f.get("thumbnail_url", "") or ""
            match_uuid = re.search(r"stream\.drime\.cloud\/([a-f0-9-]+)\/", thumbnail)

            if not match_uuid:
                continue

            stream_uuid = match_uuid.group(1)
            hls_url = f"{WORKER_BASE}/master/{stream_uuid}/playlist.m3u8"

            episodes.append(
                Episode(
                    series_key=series_key,
                    number=ep_num,
                    filename=name,
                    drime_hash=drime_hash,
                    stream_uuid=stream_uuid,
                    hls_url=hls_url,
                )
            )

    # Deduplicate by episode number (keep first found)
    seen = set()
    unique = []
    for ep in episodes:
        if ep.number not in seen:
            seen.add(ep.number)
            unique.append(ep)

    unique.sort(key=lambda x: x.number)
    print(f"[{series_key}] Scraped {len(unique)} episodes")
    return unique


def scrape_all_series() -> Dict[str, List[Episode]]:
    cookies, xsrf = get_drime_cookies()

    result = {}
    for series_key in MEMORIA_PAGES:
        result[series_key] = scrape_series(series_key, cookies, xsrf)

    return result


if __name__ == "__main__":
    result = scrape_all_series()
    for key, eps in result.items():
        print(f"{key}: {len(eps)} episodes")
