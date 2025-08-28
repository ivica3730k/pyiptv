import asyncio
import logging
from typing import Any, List

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from pyiptv.dao.channel_retreival.base import BaseChannelRetrieval
from pyiptv.dao.channel_storage.base import BaseChannelStorage
from pyiptv.dto.channel import ChannelEntity
from pyiptv.enum.channel_type import ChannelType
from pyiptv.players.base import BasePlayer

logger = logging.getLogger(__name__)


class CLIService:
    def __init__(
        self,
        channel_storage: BaseChannelStorage,
        channel_retreival: BaseChannelRetrieval,
        player: BasePlayer,
    ) -> None:
        self.channel_storage: BaseChannelStorage = channel_storage
        self.channel_retreival: BaseChannelRetrieval = channel_retreival
        self.player: BasePlayer = player

        self.current_matches: List[ChannelEntity] = []
        self.selected_index: int = 0
        self.view_start_index: int = 0
        self.max_visible_rows: int = 30
        self.last_query: str = ""

        for channel_list in self.channel_retreival.retreive_channels_by_type(
            ChannelType.LIVE, page_size=10000
        ):
            self.channel_storage.save_channel_bulk(channel_list)

        self.output_field: TextArea = TextArea(
            style="class:output",
            scrollbar=True,
            focusable=False,
            wrap_lines=False,
        )

        self.help_bar: TextArea = TextArea(
            text="Up/Down to navigate  |  ENTER to play  |  Ctrl+C to quit",
            style="class:help",
            height=1,
            focusable=False,
        )

        self.input_field: TextArea = TextArea(
            height=1,
            prompt="Search: ",
            style="class:input",
            multiline=False,
            wrap_lines=False,
        )

        self.input_field.buffer.on_text_changed += self.on_text_change

        self.container: HSplit = HSplit(
            [
                self.output_field,
                self.help_bar,
                self.input_field,
            ],
            padding=0,
        )

        self.kb: KeyBindings = KeyBindings()
        self.kb.add("c-c")(self.exit_app)
        self.kb.add("up")(self.move_up)
        self.kb.add("down")(self.move_down)
        self.kb.add("enter")(self.play_selected)

        self.application: Application[Any] = Application(
            layout=Layout(self.container),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=False,
            style=Style.from_dict(
                {
                    "output": "bg:#000000 #ffffff",
                    "input": "bg:#1a1a1a #ffffff",
                    "help": "bg:#333333 #aaaaaa",
                }
            ),
        )

    def exit_app(self, event: KeyPressEvent) -> None:
        event.app.exit()

    def on_text_change(self, _: Any) -> None:
        asyncio.get_event_loop().call_soon(self.update_output)

    def move_up(self, event: KeyPressEvent) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            if self.selected_index < self.view_start_index:
                self.view_start_index = self.selected_index
            self.update_output()

    def move_down(self, event: KeyPressEvent) -> None:
        if self.selected_index + 1 < len(self.current_matches):
            self.selected_index += 1
            if self.selected_index >= self.view_start_index + self.max_visible_rows:
                self.view_start_index = self.selected_index - self.max_visible_rows + 1
            self.update_output()

    def play_selected(self, event: KeyPressEvent) -> None:
        if 0 <= self.selected_index < len(self.current_matches):
            selected_channel: ChannelEntity = self.current_matches[self.selected_index]
            logger.info(f"Playing channel: {selected_channel.name}")
            self.player.play(selected_channel.playable_url)

    def update_output(self) -> None:
        query: str = self.input_field.text.strip()
        if not query:
            self.output_field.text = ""
            self.current_matches = []
            self.selected_index = 0
            self.view_start_index = 0
            self.last_query = ""
            return

        try:
            self.current_matches: List[ChannelEntity] = (
                self.channel_storage.search_by_name_and_type(
                    name=query, channel_type=ChannelType.LIVE
                )
            )
        except Exception:
            logger.exception("Search failed")
            self.current_matches = []

        if query != self.last_query:
            self.selected_index = 0
            self.view_start_index = 0
            self.last_query = query

        self.selected_index = max(
            0, min(self.selected_index, len(self.current_matches) - 1)
        )

        if self.selected_index < self.view_start_index:
            self.view_start_index = self.selected_index
        elif self.selected_index >= self.view_start_index + self.max_visible_rows:
            self.view_start_index = self.selected_index - self.max_visible_rows + 1

        lines: List[str] = [f"{'':<3}{'ID':<8} | Name", f"{'':<3}{'-' * 30}"]

        visible_items = self.current_matches[
            self.view_start_index : self.view_start_index + self.max_visible_rows
        ]

        for i, ch in enumerate(visible_items):
            actual_index = self.view_start_index + i
            prefix = ">>" if actual_index == self.selected_index else "  "
            lines.append(f"{prefix} {ch.id:<8} | {ch.name}")

        self.output_field.text = "\n".join(lines)

    def run(self) -> None:
        logger.info("Starting interactive CLI UI")
        with patch_stdout():
            self.application.run()
