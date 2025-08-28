import os
import random
import string
import tempfile
import time
import unittest

from pyiptv.dto.channel import ChannelEntity
from pyiptv.enum.channel_type import ChannelType
from pyiptv.dao.channel_storage.sqlite import ChannelStorageSQLite


def random_word(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_channel_name() -> str:
    words = [random_word(random.randint(3, 8)) for _ in range(random.randint(1, 8))]
    return " ".join(words)


class TestChannelStorageSQLite(unittest.TestCase):
    def setUp(self):
        temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.addCleanup(lambda: os.remove(temp_db_file.name))
        self.storage = ChannelStorageSQLite(temp_db_file.name)

    def test_save_and_get_channel(self):
        ch = ChannelEntity(
            id="1",
            name="LoremTV",
            playable_url="http://lorem.test",
            type=ChannelType.LIVE,
        )
        self.storage.save_channel(ch)

        fetched = self.storage.get_channel("1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched, ch)  # dataclass equality

    def test_search_by_exact_name(self):
        ch = ChannelEntity(
            id="1",
            name="IpsumNet",
            playable_url="http://ipsum.test",
            type=ChannelType.LIVE,
        )
        self.storage.save_channel(ch)

        results = self.storage.search_by_name_and_type("ipsumnet", ChannelType.LIVE)
        self.assertIn(ch, results)  # dataclass membership

    def test_search_by_prefix(self):
        ch = ChannelEntity(
            id="1",
            name="DolorStream",
            playable_url="http://dolor.test",
            type=ChannelType.LIVE,
        )
        self.storage.save_channel(ch)

        results = self.storage.search_by_name_and_type("dol", ChannelType.LIVE)
        self.assertIn(ch, results)

    def test_search_by_substring(self):
        ch = ChannelEntity(
            id="1",
            name="SitPlay",
            playable_url="http://sit.test",
            type=ChannelType.LIVE,
        )
        self.storage.save_channel(ch)

        results = self.storage.search_by_name_and_type("pla", ChannelType.LIVE)
        self.assertIn(ch, results)

    def test_search_multiword(self):
        ch = ChannelEntity(
            id="2",
            name="Amet Sport Alpha",
            playable_url="http://amet.test",
            type=ChannelType.LIVE,
        )
        self.storage.save_channel(ch)

        results = self.storage.search_by_name_and_type("amet alpha", ChannelType.LIVE)
        self.assertIn(ch, results)

    def test_search_by_name_and_type(self):
        ch1 = ChannelEntity(
            id="1",
            name="ConsecteturTV",
            playable_url="http://consectetur.test",
            type=ChannelType.LIVE,
        )
        ch2 = ChannelEntity(
            id="2",
            name="ConsecteturTV",
            playable_url="http://consectetur-vod.test",
            type=ChannelType.VOD,
        )
        self.storage.save_channel(ch1)
        self.storage.save_channel(ch2)

        results = self.storage.search_by_name_and_type("consecteturtv", ChannelType.VOD)
        self.assertEqual(results, [ch2])  # exact list equality

    def test_search_ranking_order(self):
        """Ensure more relevant matches are returned before less relevant ones."""
        ch1 = ChannelEntity(
            id="1",
            name="Test Channel Sports Alpha",
            playable_url="http://1",
            type=ChannelType.LIVE,
        )
        ch2 = ChannelEntity(
            id="2", name="Test Sports", playable_url="http://2", type=ChannelType.LIVE
        )
        ch3 = ChannelEntity(
            id="3", name="Test", playable_url="http://3", type=ChannelType.LIVE
        )
        ch4 = ChannelEntity(
            id="4", name="RandomTV", playable_url="http://4", type=ChannelType.LIVE
        )

        self.storage.save_channel_bulk([ch1, ch2, ch3, ch4])

        results = self.storage.search_by_name_and_type("test sports", ChannelType.LIVE)
        self.assertEqual(len(results), 2)
        expected_order = [
            ch2,
            ch1,
        ]
        self.assertEqual(results, expected_order)

    def test_special_chars_in_name(self):
        ch = ChannelEntity(
            id="1",
            name="News - Sports (HD)",
            playable_url="http://news.test",
            type=ChannelType.LIVE,
        )
        self.storage.save_channel(ch)

        results = self.storage.search_by_name_and_type(
            "news - sports", ChannelType.LIVE
        )
        self.assertIn(ch, results)


class TestChannelStoragePerformance(unittest.TestCase):
    def setUp(self):
        temp_db_file = tempfile.NamedTemporaryFile(delete_on_close=True)
        self.addCleanup(lambda: os.remove(temp_db_file.name))
        self.storage = ChannelStorageSQLite(temp_db_file.name)

    def test_bulk_insert_and_search_performance_2000(self):
        self.test_bulk_insert_and_search_performance(
            total_channels=2000, insert_time_limit=0.1, search_time_limit=0.01
        )

    def test_bulk_insert_and_search_performance_20000(self):
        self.test_bulk_insert_and_search_performance(
            total_channels=20000, insert_time_limit=1, search_time_limit=0.01
        )

    def test_bulk_insert_and_search_performance_200000(self):
        self.test_bulk_insert_and_search_performance(
            total_channels=200000, insert_time_limit=10, search_time_limit=0.01
        )

    def test_bulk_insert_and_search_performance(
        self,
        total_channels: int = 200,
        insert_time_limit: float = 0.1,
        search_time_limit: float = 0.01,
    ):
        target_channel = ChannelEntity(
            id="test-id",
            name="Extreme Sports Channel HD",
            playable_url="http://localhost/test",
            type=ChannelType.LIVE,
        )

        # Generate random dummy channels
        dummy_channels = [
            ChannelEntity(
                id=f"dummy-{i}",
                name=random_channel_name(),
                playable_url=f"http://localhost/{i}",
                type=ChannelType.LIVE,
            )
            for i in range(total_channels)
        ]

        # Insert dummy + target channel in one bulk op
        all_channels = dummy_channels + [target_channel]

        start_insert = time.perf_counter()
        self.storage.save_channel_bulk(all_channels)
        duration_insert = time.perf_counter() - start_insert

        self.assertLess(
            duration_insert,
            insert_time_limit,
            f"Bulk insert took too long: {duration_insert:.2f}s",
        )

        # Search by partial multiword name
        start_search = time.perf_counter()
        results = self.storage.search_by_name_and_type("sports hd", ChannelType.LIVE)
        duration_search = time.perf_counter() - start_search

        self.assertLess(
            duration_search,
            search_time_limit,
            f"Search took too long: {duration_search:.3f}s",
        )
        self.assertTrue(
            any(r.id == target_channel.id for r in results),
            "Target channel not found in search results",
        )
