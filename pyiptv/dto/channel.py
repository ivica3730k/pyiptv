import dataclasses

from pyiptv.enum.channel_type import ChannelType


@dataclasses.dataclass
class ChannelEntity:
    id: str
    name: str
    playable_url: str
    type: ChannelType
