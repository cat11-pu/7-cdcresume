# cdcresume

纯 Python 标准库的 cdcresume（无第三方依赖）。

## 用法

- `Journal.append(key, value)`：追加变更，返回连续递增的 seq；`latest` 为最新值视图。
- `Journal.since(start)`：返回 seq 严格大于 `start` 的变更（左开，按 seq 升序）。
- `Journal.dump()` / `Journal.load(blob)`：落盘/重放；尾部半条记录忽略并计入 `truncated`。
- `Syncer.snapshot(state)`：落快照，把快照覆盖到的最大 seq 记为水位。
- `Syncer.resume(cursor)`：从 `cursor + 1` 接着拉，不漏不重叠。
- `Syncer.apply(batch)`：幂等应用，重复条目计入 `duplicates`。

日志与去重都只保留水位与最近窗口，内存不随变更总量线性增长。

## 测试

    python3 -m unittest discover -s tests -v

## 场景自检

    python3 check_sample.py
