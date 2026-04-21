import urllib.request
from dataclasses import dataclass
from typing import Dict, List


WORKER_BASE = "https://selecta-vision-proxy.edersonff.workers.dev"

SERIES_CONFIG = {
    "dbz": {
        "prefix": "DBZ",
        "mdtv_path": "Dragon%20Ball%20Z",
        "max_guess": 400,
    },
    "db": {
        "prefix": "DBC",
        "mdtv_path": "Dragon%20Ball%20Classico",
        "max_guess": 300,
    },
}

MDTV_BASE = "https://cloud.mdtvdown.workers.dev/0:/Animes/Dragon%20Ball/Anime"


@dataclass
class Episode:
    series_key: str
    number: int
    filename: str
    direct_url: str


def _probe_episode(prefix: str, ep_num: int, mdtv_path: str) -> int:
    filename = f"{prefix}.{ep_num:03d}.BD1080p.MemoriadaTV.Remux.mkv"
    url = f"{MDTV_BASE}/{mdtv_path}/Remux/{filename}"
    req = urllib.request.Request(url, headers={
        "Range": "bytes=0-0",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def _find_max_episode(prefix: str, mdtv_path: str, max_guess: int) -> int:
    lo, hi = 1, max_guess
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _probe_episode(prefix, mid, mdtv_path) == 206:
            lo = mid
        else:
            hi = mid - 1
    return lo


def generate_episodes(series_key: str) -> List[Episode]:
    config = SERIES_CONFIG[series_key]
    prefix = config["prefix"]
    mdtv_path = config["mdtv_path"]

    count = _find_max_episode(prefix, mdtv_path, config["max_guess"])
    print(f"[{series_key}] Found {count} episodes (probed via binary search)")

    episodes = []
    for num in range(1, count + 1):
        filename = f"{prefix}.{num:03d}.BD1080p.MemoriadaTV.Remux.mkv"
        episodes.append(
            Episode(
                series_key=series_key,
                number=num,
                filename=filename,
                direct_url=f"{WORKER_BASE}/mdtv/{filename}",
            )
        )
    return episodes


def scrape_all_series() -> Dict[str, List[Episode]]:
    return {
        "dbz": generate_episodes("dbz"),
        "db": generate_episodes("db"),
    }


if __name__ == "__main__":
    result = scrape_all_series()
    for key, eps in result.items():
        print(f"{key}: {len(eps)} episodes")
