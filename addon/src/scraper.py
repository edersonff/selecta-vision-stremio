import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from gdrive import list_gdrive_files


WORKER_BASE = "https://selecta-vision-proxy.edersonff.workers.dev"

GDRIVE_FOLDER_ID = "1trhkrfBp94vjWyYO-PUaBDy0T80ErWfi"


@dataclass
class Episode:
    series_key: str
    number: int
    filename: str
    file_hash: str
    shareable_link_id: str
    direct_url: str


def parse_episode_number(filename: str, series_key: str) -> Optional[int]:
    patterns = {
        "dbz": [r"DBZ[_.\s-]?(\d+)", r"DBZ\.(\d+)"],
        "db": [r"DB[_.\s-]?(\d+)", r"DB\.(\d+)"],
    }

    for pattern in patterns.get(series_key, [r"(\d+)"]):
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1))

    match = re.search(r"\.(\d{3})\.", filename)
    if match:
        return int(match.group(1))

    return None


def scrape_series(series_key: str) -> List[Episode]:
    files = list_gdrive_files(GDRIVE_FOLDER_ID)
    print(f"[{series_key}] Found {len(files)} files")

    episodes = []
    for f in files:
        name = f.get("name", "")
        ep_num = parse_episode_number(name, series_key)

        if not ep_num:
            continue

        file_id = f.get("id", "")
        if not file_id:
            continue

        direct_url = f"{WORKER_BASE}/mdtv/{name}"

        episodes.append(
            Episode(
                series_key=series_key,
                number=ep_num,
                filename=name,
                file_hash=file_id,
                shareable_link_id="",
                direct_url=direct_url,
            )
        )

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
    return {"dbz": scrape_series("dbz")}


if __name__ == "__main__":
    result = scrape_all_series()
    for key, eps in result.items():
        print(f"{key}: {len(eps)} episodes")
