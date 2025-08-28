from abc import ABC, abstractmethod
from typing import Generator, List

from pyiptv.dto.channel import ChannelEntity
from pyiptv.enum.channel_type import ChannelType


class BaseChannelRetrieval(ABC):
    @abstractmethod
    def retreive_channels_by_type(
        self, channel_type: ChannelType, page_size: int
    ) -> Generator[List[ChannelEntity], None, None]:
        pass
