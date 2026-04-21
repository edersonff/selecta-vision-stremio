from dataclasses import dataclass
from typing import Dict, List


WORKER_BASE = "https://selecta-vision-proxy.edersonff.workers.dev"

SERIES_FILE_PATTERNS = {
    "dbz": {"prefix": "DBZ", "count": 200},
    "db": {"prefix": "DBC", "count": 153},
}


@dataclass
class Episode:
    series_key: str
    number: int
    filename: str
    direct_url: str


def generate_episodes(series_key: str) -> List[Episode]:
    pattern = SERIES_FILE_PATTERNS[series_key]
    prefix = pattern["prefix"]
    count = pattern["count"]

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

    print(f"[{series_key}] Generated {len(episodes)} episodes ({prefix}.001-{prefix}.{count:03d})")
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
