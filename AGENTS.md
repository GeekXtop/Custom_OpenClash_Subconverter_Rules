# 仓库指南

默认语言简体中文。

本项目只维护公开的 SubConverter-Extended INI 模板、自定义规则源、外部规则源声明和生成后的 Clash rule-provider YAML。最终 `config.yaml` 由本地 SubConverter-Extended 生成，不提交。

Python 使用 `uv` 管理。

## 常用命令

- `uv run pytest`
- `uv run python tools/sync_cfg.py`
- `uv run python tools/sync_sources.py`
- `uv run python tools/generate_rules.py`
- `uv run python tools/generate_cfg.py`
- `git diff --check`

## 约定

- `vendor/cfg/` 存放上游 INI 快照。
- `vendor/rules/` 存放上游规则同步快照。
- `local/cfg/` 存放本地 INI 派生声明。
- `local/rules/` 存放手写规则源和删除规则。
- `dist/cfg/` 存放对外发布的 INI。
- `dist/rules/` 存放对外发布的 YAML 规则集。
- 不生成 `.mrs`。
- 不提交订阅链接、最终 `config.yaml`、provider 缓存或本地环境文件。
