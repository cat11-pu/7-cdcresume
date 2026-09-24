"""syncer.py：同步门面（基线：只能全量重来）。"""
from __future__ import annotations

from syncjournal import Journal


class Syncer:
    def __init__(self, journal: Journal):
        self.journal = journal
        self.fetched = 0
        self.duplicates = 0
        self.resumed = 0

    def snapshot(self, state) -> dict:
        return dict(state)

    def resume(self, cursor: int) -> dict:
        raise NotImplementedError("断点续传还没实现")

    def apply(self, batch) -> int:
        raise NotImplementedError("幂等应用还没实现")
