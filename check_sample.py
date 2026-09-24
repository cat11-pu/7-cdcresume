"""把 sample/sync.json 跑一遍，打印验收面（两个子系统）。"""
import json
import os
import sys

from syncjournal import Journal
from syncer import Syncer


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("sample", "sync.json")
    with open(path, encoding="utf-8") as handle:
        spec = json.load(handle)
    journal = Journal()
    for item in spec["changes"]:
        journal.append(item["key"], item["value"])
    syncer = Syncer(journal)
    first = syncer.resume(0)
    print("首轮拉取条数 =", len(first["entries"]))
    print("首轮水位 =", first["cursor"])
    journal.append("a", "late")
    journal.append("d", "new")
    second = syncer.resume(first["cursor"])
    print("续拉条数 =", len(second["entries"]))
    print("续拉内容 =", [(e["seq"], e["key"]) for e in second["entries"]])
    blob = journal.dump()
    fresh = Journal()
    fresh.load(blob[:-4] + b"xx")
    print("重启后重放条数 =", fresh.seq)
    print("残尾忽略 =", fresh.truncated)
    print("幂等应用（重复提交同一批） =", syncer.apply(second["entries"]))
    print("快照与增量边界对齐 =", syncer.resume(first["cursor"])["cursor"] == journal.seq)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
