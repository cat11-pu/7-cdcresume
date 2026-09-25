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


class TestPersistence(unittest.TestCase):
    def test_since_left_open_and_ordered(self):
        journal = Journal()
        for key in ("a", "b", "c"):
            journal.append(key, key)
        self.assertEqual([e["seq"] for e in journal.since(1)], [2, 3])
        self.assertEqual(journal.since(3), [])

    def test_dump_load_roundtrip(self):
        journal = Journal()
        journal.append("a", "1")
        journal.append("b", "2")
        journal.append("a", "3")
        fresh = Journal()
        self.assertEqual(fresh.load(journal.dump()), 3)
        self.assertEqual(fresh.seq, journal.seq)
        self.assertEqual(fresh.since(0), journal.since(0))
        self.assertEqual(fresh.latest, journal.latest)
        self.assertEqual(fresh.truncated, 0)

    def test_load_ignores_torn_tail(self):
        journal = Journal()
        for seq in range(5):
            journal.append("k%d" % seq, "v%d" % seq)
        blob = journal.dump()
        fresh = Journal()
        fresh.load(blob[:-4] + b"xx")
        self.assertEqual(fresh.seq, 5)
        self.assertEqual(fresh.truncated, 1)


class TestSyncer(unittest.TestCase):
    def test_resume_from_watermark(self):
        journal = Journal()
        syncer = Syncer(journal)
        journal.append("a", "1")
        first = syncer.resume(0)
        journal.append("b", "2")
        second = syncer.resume(first["cursor"])
        self.assertEqual([e["seq"] for e in second["entries"]], [2])
        self.assertEqual(second["cursor"], journal.seq)

    def test_snapshot_watermark_aligned(self):
        journal = Journal()
        syncer = Syncer(journal)
        journal.append("a", "1")
        syncer.snapshot({"a": "1"})
        self.assertEqual(syncer.watermark, 1)
        journal.append("b", "2")
        self.assertEqual([e["seq"] for e in syncer.resume(syncer.watermark)["entries"]], [2])

    def test_apply_idempotent(self):
        journal = Journal()
        syncer = Syncer(journal)
        journal.append("a", "1")
        batch = syncer.resume(0)["entries"]
        self.assertEqual(syncer.apply(batch), 1)
        self.assertEqual(syncer.apply(batch), 0)
        self.assertEqual(syncer.duplicates, 1)
        self.assertEqual(syncer.state, {"a": "1"})


if __name__ == "__main__":
    unittest.main()
