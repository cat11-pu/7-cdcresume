import unittest

from syncjournal import Journal
from syncer import Syncer


class TestJournal(unittest.TestCase):
    def test_seq_advances(self):
        journal = Journal()
        first = journal.append("a", "1")
        second = journal.append("b", "2")
        self.assertEqual(second, first + 1)

    def test_latest_kept(self):
        journal = Journal()
        journal.append("a", "1")
        self.assertEqual(journal.latest["a"], "1")

    def test_snapshot_copy(self):
        syncer = Syncer(Journal())
        state = {"a": "1"}
        self.assertEqual(syncer.snapshot(state), state)

    def test_counters(self):
        syncer = Syncer(Journal())
        self.assertEqual((syncer.fetched, syncer.duplicates, syncer.resumed), (0, 0, 0))

    def test_since_empty_at_start(self):
        self.assertEqual(Journal().since(0), [])


if __name__ == "__main__":
    unittest.main()
