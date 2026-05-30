# Custom OpenClash SubConverter Rules

这个仓库用于维护一个公开的 `SubConverter-Extended` INI 模板和配套规则集。

## 目标

- 维护一个公开 INI：`dist/cfg/Custom_Clash_Full_Plus.ini`
- 维护本地自定义规则：`local/rules/*.list`
- 声明并同步外部规则：`sources.yaml`
- 生成公开 YAML 规则集：`dist/rules/*.yaml`
- 不提交最终 `config.yaml`
- 不生成 `.mrs`

## 工作流

```powershell
uv run python tools/sync_cfg.py
uv run python tools/sync_sources.py
uv run python tools/generate_rules.py
uv run python tools/generate_cfg.py
uv run pytest
git diff --check
```

`sync_cfg.py` 会把 Aethersailor 的 `cfg/Custom_Clash_Full.ini` 同步到 `vendor/cfg/Custom_Clash_Full.ini`。`generate_cfg.py` 会读取 `local/cfg/full-plus.yaml`，应用仓库路径替换、规则文件名替换和 Crypto 插入锚点，生成 `dist/cfg/Custom_Clash_Full_Plus.ini`。

`sync_sources.py` 只同步 `sources.yaml` 中 `enabled: true` 的外部规则源。当前基础直连、代理补充、Steam CDN 和非标端口规则来自 Aethersailor/Custom_OpenClash_Rules，Crypto 外部补充来自 ACL4SSR 和 Dler。

可以同时声明多个上游。`external_sources` 只负责“拉哪份外部文件到 `vendor/rules/`”，`rulesets` 决定“哪些外部文件和本地文件合并成某个公开 rule-provider”，`local/cfg/*.yaml` 决定“这个 rule-provider 在 INI 里挂到哪个策略组”。因此选择某个上游的某个分组，本质上就是在 `sources.yaml` 里新增对应 URL，然后只把它加入需要的 `rulesets.sources`。

基础规则生成逻辑：

```text
Custom_Direct =
  vendor/rules/Aethersailor_Custom_Direct.list
  + local/rules/Custom_Direct.list
  - local/rules/remove.list

Custom_Proxy =
  vendor/rules/Aethersailor_Custom_Proxy.list
  + local/rules/Custom_Proxy.list
  - local/rules/remove.list

Steam_CDN =
  vendor/rules/Aethersailor_Steam_CDN.list
  - local/rules/remove.list

Custom_Port_Direct =
  vendor/rules/Aethersailor_Custom_Port_Direct.yaml
  - local/rules/remove.list
```

Crypto 规则生成逻辑：

```text
External_Crypto_Domain.yaml =
  vendor/rules/ACL4SSR_Crypto.list
  + vendor/rules/Dler_Crypto.yaml
  - local/rules/remove.list
```

INI 中仍然保留 `GEOSITE,category-cryptocurrency`，`External_Crypto_Domain.yaml` 只作为补充。生成阶段不对 geosite 做去重，避免本仓库同步到的 geosite 数据与用户路由器本地 geosite 版本不一致时漏规则。

## 本地使用

1. 将 `dist/cfg/Custom_Clash_Full_Plus.ini` 发布到 GitHub raw 或 jsDelivr。
2. 在本地 `SubConverter-Extended` 中传入你的订阅链接和该 INI。
3. 生成最终 `config.yaml`。
4. 将最终配置推送或复制到路由器。

`config.yaml`、订阅链接和 provider 缓存属于本地私有产物，已写入 `.gitignore`。

## 目录

```text
vendor/cfg/          上游 INI 快照
vendor/rules/        上游规则同步快照
local/cfg/           本地 INI 派生声明
local/rules/         手写规则源
dist/cfg/            对外发布 INI
dist/rules/          对外发布 YAML 规则集
tools/               同步和生成脚本
tests/               规则转换测试
```
