from dataclasses import dataclass
from typing import List


@dataclass
class Episode:
    number: int
    download_id: str


@dataclass
class Series:
    id: str
    name: str
    poster: str
    episodes: List[Episode]


MEMORIA_TV_BASE_URL = "https://www.memoriadatv.com"
DRIME_BASE_URL = "https://dri.me"

SERIES_DOWNLOAD_PAGES = {
    "dbz": "https://www.memoriadatv.com/dragon-ball-z-1989-1996-dual-audio-bluray-1080p/",
    "db": "https://www.memoriadatv.com/dragon-ball-1986-1989-dual-audio-bluray-1080p/",
}

SOURCE_URL = "https://40thproject.ai"
DOWNLOAD_BASE_URL = "https://downloads.40thproject.ai/api/public/dl/"
REFERER_HEADER = {"Referer": "https://40thproject.ai/"}

ADDON_ID = "selectavision.stremio"
ADDON_VERSION = "1.0.0"
ADDON_NAME = "SelectaVision"
ADDON_DESCRIPTION = "Dragon Ball em HD - Dual Áudio (PT-BR/JP)"

SERIES_TEMPLATES = {
    "dbz": {
        "ids": ["tt0121220", "tt0214341"],
        "name": "Dragon Ball Z",
        "poster": "https://static.vakinha.com.br/uploads/vakinha/image/566433/mtv.png?ims=700x410",
    },
    "db": {
        "ids": ["tt0088509", "tt0280249"],
        "name": "Dragon Ball",
        "poster": "https://static.vakinha.com.br/uploads/vakinha/image/566433/mtv.png?ims=700x410",
    },
}

VIDEO_SIZE_APPROX = 6400000000
STREAM_FPS = "23.976"
STREAM_RESOLUTION = "1080p"
