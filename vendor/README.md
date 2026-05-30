# Vendor 快照

此目录保存从上游同步下来的快照文件:

- `cfg/`: 上游 INI 模板快照。
- `rules/`: 上游规则文件快照。

不要直接编辑这里的文件。需要更新上游内容时，修改 `sources.yaml` 或 `local/cfg/*.yaml` 中的 URL，然后运行:

```powershell
uv run python tools/sync_cfg.py
uv run python tools/sync_sources.py
```

需要新增、覆盖或删除规则时，优先修改 `local/rules/` 和 `sources.yaml`。
