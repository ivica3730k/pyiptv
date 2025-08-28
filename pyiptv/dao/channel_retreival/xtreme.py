import logging
from typing import Generator, List

import requests

from pyiptv.dao.channel_retreival.base import BaseChannelRetrieval
from pyiptv.dto.channel import ChannelEntity
from pyiptv.enum.channel_type import ChannelType

logger = logging.getLogger(__name__)


class XtremeChannelSource(BaseChannelRetrieval):
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

    def retreive_channels_by_type(
        self, channel_type: ChannelType, page_size: int = 10000
    ) -> Generator[List[ChannelEntity], None, None]:
        if channel_type != ChannelType.LIVE:
            raise NotImplementedError(
                "Only LIVE channel type is supported by Xtreme channel retrieval for now."
            )

        url = f"{self.base_url}/player_api.php"
        params = {
            "username": self.username,
            "password": self.password,
            "action": "get_live_streams",
        }

        try:
            logger.debug(f"Requesting live streams from {url}")
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            streams = response.json()

            logger.info(f"Retrieved {len(streams)} live streams")

            batch: List[ChannelEntity] = []

            for stream in streams:
                stream_id = stream.get("stream_id")
                name = stream.get("name", "").strip()

                playable_url = f"{self.base_url}/live/{self.username}/{self.password}/{stream_id}.ts"

                batch.append(
                    ChannelEntity(
                        id=str(stream_id),
                        name=name,
                        playable_url=playable_url,
                        type=ChannelType.LIVE,
                    )
                )

                if len(batch) >= page_size:
                    logger.debug(f"Yielding batch of {len(batch)} channels")
                    yield batch
                    batch = []

            if batch:
                logger.debug(f"Yielding batch of {len(batch)} channels")
                yield batch

        except requests.RequestException as e:
            logger.error(f"HTTP error while retrieving live streams: {e}")
        except ValueError as e:
            logger.error(f"Failed to parse JSON from live streams response: {e}")
