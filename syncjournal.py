"""syncjournal.py：变更日志（连续序号 + 持久化 + 有界窗口）。"""
from __future__ import annotations

import json
from collections import deque


class Journal:
    """只保留水位与最近窗口的变更日志。

    - seq 严格递增，每条变更 +1；
    - latest 始终是最新值视图（老调用方依赖）；
    - 仅保留最近 WINDOW 条变更供 since/续拉使用，
      内存占用不随变更总量线性增长。
    """

    WINDOW = 1024

    def __init__(self):
        self.latest = {}
        self.seq = 0
        self.appended = 0
        self.truncated = 0
        self._entries = deque()

    def append(self, key, value) -> int:
        self.seq += 1
        self.appended += 1
        self.latest[key] = value
        self._entries.append({"seq": self.seq, "key": key, "value": value})
        while len(self._entries) > self.WINDOW:
            self._entries.popleft()
        return self.seq

    def since(self, start: int) -> list:
        """返回 seq 严格大于 start 的全部变更（左开，按 seq 升序）。"""
        return [dict(entry) for entry in self._entries if entry["seq"] > start]

    def dump(self) -> bytes:
        """落盘：首行为水位元信息，其后每行一条变更记录。"""
        lines = [json.dumps({"type": "meta", "seq": self.seq, "appended": self.appended})]
        lines.extend(json.dumps(entry) for entry in self._entries)
        return ("\n".join(lines) + "\n").encode("utf-8")

    def load(self, blob: bytes) -> int:
        """载入并重放日志，返回重放的变更条数。

        尾部不完整的半条记录（缺少换行结尾）忽略并计入 truncated；
        无法解析的整行同样忽略并计入 truncated。
        """
        self.latest = {}
        self.seq = 0
        self.appended = 0
        self.truncated = 0
        self._entries = deque()
        lines = blob.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        elif lines:
            self.truncated += 1
            lines.pop()
        replayed = 0
        for raw in lines:
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                self.truncated += 1
                continue
            if not isinstance(record, dict):
                self.truncated += 1
                continue
            if record.get("type") == "meta":
                self.seq = int(record.get("seq", 0))
                self.appended = int(record.get("appended", 0))
                continue
            try:
                seq = int(record["seq"])
                key = record["key"]
                value = record["value"]
            except (KeyError, TypeError, ValueError):
                self.truncated += 1
                continue
            self.latest[key] = value
            self._entries.append({"seq": seq, "key": key, "value": value})
            replayed += 1
        while len(self._entries) > self.WINDOW:
            self._entries.popleft()
        return replayed
