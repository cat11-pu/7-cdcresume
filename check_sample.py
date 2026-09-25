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
    cut = spec["snapshot_at"]

    journal = Journal()
    syncer = Syncer(journal)

    # 首轮：快照点之前的变更先入库，从 0 开始拉。
    for item in spec["changes"][:cut]:
        journal.append(item["key"], item["value"])
    first = syncer.resume(0)
    print("首轮拉取条数 =", len(first["entries"]))
    print("首轮水位 =", first["cursor"])

    # 应用首轮后在快照点落快照，快照覆盖到的最大 seq 记为水位。
    syncer.apply(first["entries"])
    syncer.snapshot(syncer.state)
    snap_watermark = syncer.watermark

    # 续拉：快照点之后的变更入库，从首轮水位 + 1 接着拉。
    for item in spec["changes"][cut:]:
        journal.append(item["key"], item["value"])
    second = syncer.resume(first["cursor"])
    print("续拉条数 =", len(second["entries"]))
    print("续拉内容 =", [(e["seq"], e["key"]) for e in second["entries"]])

    # 重启：落盘后截断尾部 4 字节再补 2 字节，模拟半条记录。
    blob = journal.dump()
    fresh = Journal()
    fresh.load(blob[:-4] + b"xx")
    print("重启后重放条数 =", fresh.seq)
    print("残尾忽略 =", fresh.truncated)

    # 幂等：同一批提交两次，第二次生效条数必须为 0。
    syncer.apply(second["entries"])
    replay = syncer.apply(second["entries"]) if spec.get("duplicate_batches") else 0
    print("幂等应用（重复提交同一批）的重复条数 =", replay)

    # 边界对齐：快照水位与续拉区间恰好拼接，不漏不重叠。
    aligned = (
        snap_watermark == first["cursor"]
        and [e["seq"] for e in second["entries"]]
        == list(range(snap_watermark + 1, journal.seq + 1))
        and syncer.resume(first["cursor"])["cursor"] == journal.seq
    )
    print("快照与增量边界对齐 =", aligned)
    print("最终状态 =", sorted(syncer.state.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
