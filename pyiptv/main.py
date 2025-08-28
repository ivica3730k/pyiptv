import logging
import os

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    filename="pyiptv.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

import tempfile

from pyiptv.dao.channel_retreival.xtreme import XtremeChannelSource
from pyiptv.dao.channel_storage.sqlite import ChannelStorageSQLite
from pyiptv.players.vlc import VLCPlayer
from pyiptv.services.cli import CLIService


def main():
    xtreme_url = os.getenv("XTREME_URL", "")
    xtreme_username = os.getenv("XTREME_USERNAME", "")
    xtreme_password = os.getenv("XTREME_PASSWORD", "")

    if not all([xtreme_url, xtreme_username, xtreme_password]):
        raise ValueError(
            "XTREME_URL, XTREME_USERNAME, and XTREME_PASSWORD must be set in environment variables."
        )

    with tempfile.NamedTemporaryFile() as temp_db_file:
        storage = ChannelStorageSQLite(temp_db_file.name)

        xtreme_source = XtremeChannelSource(
            base_url=xtreme_url,
            username=xtreme_username,
            password=xtreme_password,
        )

        vlc_player = VLCPlayer()

        cli_service = CLIService(
            channel_storage=storage, channel_retreival=xtreme_source, player=vlc_player
        )

        cli_service.run()


if __name__ == "__main__":
    main()
