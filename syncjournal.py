"""syncjournal.py：变更日志（基线：只留最新值，序号不连续）。"""
from __future__ import annotations


class Journal:
    def __init__(self):
        self.latest = {}
        self.seq = 0
        self.appended = 0
        self.truncated = 0

    def append(self, key, value) -> int:
        self.seq += 1
        self.appended += 1
        self.latest[key] = value
        return self.seq

    def since(self, start: int) -> list:
        return []

    def dump(self) -> bytes:
        raise NotImplementedError("落盘还没实现")

    def load(self, blob: bytes) -> int:
        raise NotImplementedError("载入还没实现")
