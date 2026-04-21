import json
import os
from typing import Dict, List

from config import (
    ADDON_ID,
    ADDON_VERSION,
    ADDON_NAME,
    ADDON_DESCRIPTION,
    SERIES_TEMPLATES,
    VIDEO_SIZE_APPROX,
    STREAM_FPS,
    STREAM_RESOLUTION,
)
from scraper import Episode


SERIES_SEASONS = {
    "dbz": [
        (1, 39),
        (40, 74),
        (75, 107),
        (108, 139),
        (140, 165),
        (166, 194),
        (195, 219),
        (220, 253),
        (254, 291),
    ],
    "db": [
        (1, 28),
        (29, 53),
        (54, 101),
        (102, 122),
        (123, 153),
    ],
}


def get_season(episode_number: int, series_key: str = "dbz") -> int:
    for season, (start, end) in enumerate(SERIES_SEASONS.get(series_key, SERIES_SEASONS["dbz"]), 1):
        if start <= episode_number <= end:
            return season
    return 1


def get_season_episode(episode_number: int, series_key: str = "dbz") -> int:
    for season, (start, end) in enumerate(SERIES_SEASONS.get(series_key, SERIES_SEASONS["dbz"]), 1):
        if start <= episode_number <= end:
            return episode_number - start + 1
    return episode_number


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_manifest() -> dict:
    return {
        "id": ADDON_ID,
        "version": ADDON_VERSION,
        "name": ADDON_NAME,
        "description": ADDON_DESCRIPTION,
        "logo": "https://static.vakinha.com.br/uploads/vakinha/image/566433/mtv.png?ims=700x410",
        "background": "https://static.vakinha.com.br/uploads/vakinha/image/566433/mtv.png?ims=700x410",
        "contactEmail": "ederr@ederr.com",
        "resources": ["stream"],
        "types": ["series"],
        "catalogs": [],
        "idPrefixes": ["tt"],
        "behaviorHints": {
            "adult": False,
            "p2p": False,
            "configurable": False,
            "configurationRequired": False,
        },
    }


def build_stream(episode: Episode, series_key: str) -> dict:
    template = SERIES_TEMPLATES[series_key]
    return {
        "streams": [
            {
                "url": episode.direct_url,
                "name": ADDON_NAME,
                "title": f"{template['name']} Ep.{episode.number:02d} · {STREAM_RESOLUTION} · NTSC {STREAM_FPS}fps · ~6GB",
                "behaviorHints": {
                    "notWebReady": False,
                    "bingeGroup": f"selectavision-{series_key}",
                    "filename": f"{template['name']}.{episode.number:02d}.SelectaVision.{STREAM_RESOLUTION}.mkv",
                    "videoSize": VIDEO_SIZE_APPROX,
                },
            }
        ]
    }


def generate_addon_files(
    episodes_by_series: Dict[str, List[Episode]], output_dir: str = "dist"
) -> None:
    import glob as globmod
    stream_dir = f"{output_dir}/stream/series"
    for old in globmod.glob(f"{stream_dir}/*.json"):
        os.remove(old)
    ensure_dir(output_dir)
    ensure_dir(stream_dir)

    write_json(f"{output_dir}/manifest.json", build_manifest())

    total_files = 0
    for series_key, episodes in episodes_by_series.items():
        if not episodes:
            continue

        template = SERIES_TEMPLATES[series_key]

        for episode in episodes:
            stream_data = build_stream(episode, series_key)
            season = get_season(episode.number, series_key)
            season_ep = get_season_episode(episode.number, series_key)
            for series_id in template["ids"]:
                stream_id = f"{series_id}:{season}:{season_ep}"
                write_json(
                    f"{output_dir}/stream/series/{stream_id}.json",
                    stream_data,
                )
                total_files += 1

    print(f"Generated addon files in {output_dir}/")
    for key, eps in episodes_by_series.items():
        ids_count = len(SERIES_TEMPLATES[key]["ids"])
        print(
            f"  {SERIES_TEMPLATES[key]['name']}: {len(eps)} episodes x {ids_count} IDs = {len(eps) * ids_count} files"
        )
    print(f"Total stream files: {total_files}")
