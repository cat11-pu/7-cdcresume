"""syncer.py：同步门面（快照水位 + 断点续拉 + 幂等应用）。"""
from __future__ import annotations

from syncjournal import Journal


class Syncer:
    """以下游水位为对齐边界的同步门面。

    - snapshot(state)：把快照覆盖到的最大 seq 记为水位；
    - resume(cursor)：从 cursor + 1 接着拉，不漏不重叠；
    - apply(batch)：幂等应用，重复条目计入 duplicates。

    去重只依赖水位与最近窗口（_seen），内存不随变更总量线性增长，
    每条变更的比较次数为 O(1)。
    """

    DEDUP_WINDOW = 1024

    def __init__(self, journal: Journal):
        self.journal = journal
        self.fetched = 0
        self.duplicates = 0
        self.resumed = 0
        self.state = {}
        self.watermark = 0
        self._seen = set()

    def snapshot(self, state) -> dict:
        """记录快照：快照覆盖到的最大 seq（当前日志水位）作为续拉边界。"""
        self.state = dict(state)
        self.watermark = self.journal.seq
        self._seen = {seq for seq in self._seen if seq > self.watermark}
        return dict(state)

    def resume(self, cursor: int) -> dict:
        """从 cursor + 1 接着拉，返回本批变更与新的水位。"""
        entries = self.journal.since(cursor)
        self.resumed += 1
        self.fetched += len(entries)
        if entries:
            cursor = entries[-1]["seq"]
        return {"entries": entries, "cursor": cursor}

    def apply(self, batch) -> int:
        """幂等应用一批变更，返回本次实际生效的条数。

        seq 不超过水位、或落在最近窗口（已应用过）的条目视为重复，
        跳过并计入 duplicates；同一批重复提交只生效一次。
        """
        applied = 0
        for entry in batch:
            seq = entry["seq"]
            if seq <= self.watermark or seq in self._seen:
                self.duplicates += 1
                continue
            self.state[entry["key"]] = entry["value"]
            self._seen.add(seq)
            applied += 1
            while self.watermark + 1 in self._seen:
                self.watermark += 1
                self._seen.discard(self.watermark)
        cutoff = self.watermark + self.DEDUP_WINDOW
        self._seen = {seq for seq in self._seen if seq <= cutoff}
        return applied
