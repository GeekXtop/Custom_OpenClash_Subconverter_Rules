# 仓库指南

默认语言简体中文。

本项目只维护公开的 SubConverter-Extended INI 模板、自定义规则源、外部规则源声明和生成后的 Clash rule-provider YAML。最终 `config.yaml` 由本地 SubConverter-Extended 生成，不提交。

Python 使用 `uv` 管理。

## 常用命令

- `uv run pytest`
- `uv run python tools/update_all.py`
- `git diff --check`

## 约定

- `config/custom.yaml` 存放项目生成声明。
- `config/custom.sample.yaml` 存放配置字段样例。
- `config/rules/` 存放手写规则源和删除规则。
- `vendor/` 存放本地和 CI 的上游同步缓存，已忽略，不提交。
- `templates/` 存放对外发布的 INI 模板。
- `rules/` 存放对外发布的 YAML 规则集。
- `config/custom.yaml` 只声明文件名和逻辑来源，目录由脚本固定拼接。
- 不生成 `.mrs`。
- 不提交订阅链接、最终 `config.yaml`、上游缓存、provider 缓存或本地环境文件。
