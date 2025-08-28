from abc import ABC, abstractmethod
from typing import List, Optional

from pyiptv.dto.channel import ChannelEntity
from pyiptv.enum.channel_type import ChannelType


class BaseChannelStorage(ABC):
    @abstractmethod
    def save_channel(self, channel: ChannelEntity) -> None:
        pass

    @abstractmethod
    def save_channel_bulk(self, channels: List[ChannelEntity]) -> None:
        pass

    @abstractmethod
    def get_channel(self, channel_id: str) -> Optional[ChannelEntity]:
        pass

    @abstractmethod
    def search_by_name_and_type(
        self, name: str, channel_type: ChannelType
    ) -> List[ChannelEntity]:
        pass
