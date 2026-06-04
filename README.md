# Custom OpenClash SubConverter Rules

这个仓库维护一套给 OpenClash 使用的订阅转换模板和规则生成流水线。它只维护项目配置、手写规则、生成后的 Clash rule-provider YAML，以及给 SubConverter-Extended 使用的 INI 模板。上游快照只作为本地和 CI 的 `vendor/` 缓存，不提交。

本仓库不保存订阅链接，也不提交最终 `config.yaml`。最终配置由本地 SubConverter-Extended 或 `api.asailor.org` 这类 SubConverter-Extended 后端，根据订阅链接和本仓库发布的 INI 生成，再导入 OpenClash。

## 产出

- `publish` 分支的 `templates/Custom_Clash_Full_Plus.ini`：发布给 SubConverter-Extended 使用的 INI。
- `publish` 分支的 `rules/*.yaml`：INI 引用的 Clash rule-provider。

不生成或不提交：`config.yaml`、订阅链接、provider 缓存、`.mrs`、本地环境文件。

## 发布 URL

模板 URL：

```text
https://testingcf.jsdelivr.net/gh/GeekXtop/Custom_OpenClash_Subconverter_Rules@publish/templates/Custom_Clash_Full_Plus.ini
```

规则集 URL 前缀：

```text
https://testingcf.jsdelivr.net/gh/GeekXtop/Custom_OpenClash_Subconverter_Rules@publish/rules/
```

## 核心模型

本项目可以基于任意 SubConverter INI 主模板派生。当前默认模板是 Aethersailor 的 OpenClash Full INI：

```text
https://raw.githubusercontent.com/Aethersailor/Custom_OpenClash_Rules/refs/heads/main/cfg/Custom_Clash_Full.ini
```

主模板决定最终给 OpenClash 使用的规则顺序、策略组、geosite/geoip 和 provider 挂载位置。`config/custom.yaml` 是本项目唯一生效的生成声明文件，完整字段样例见 `config/custom.sample.yaml`。

- `template`：声明主模板来源、输出 INI、provider URL 前缀和锚点插入。
- `rules`：声明外部规则源、规则合并关系和 rule-provider 输出。

配置里只声明文件名和逻辑来源，目录由脚本固定，避免把 `vendor/`、`config/`、`rules/`、`templates/` 的边界暴露成可随意改的路径。

其中 `template` 段负责 INI 模板派生：

- `source.upstream_url`：主模板下载地址，可以换成 ACL4SSR 等其他 INI。
- `source.file`：主模板同步到 ignored `vendor/templates/` 缓存后的文件名。
- `output`：生成到本地 ignored `templates/` 后发布到 `publish` 分支的 INI 文件名。
- `provider_urls`：声明模板中的上游 provider URL 前缀，以及本仓库发布 provider 的 URL 前缀。
- `insertions`：在指定锚点插入额外 ruleset 或策略组。

`rules` 段不决定最终路由顺序，只负责生成主模板引用的 provider 文件：

- `external_sources`：下载外部规则到 ignored `vendor/rules/` 缓存，每项用 `file` 声明文件名。
- `remove`：共享删除源，文件固定从 `config/rules/` 读取，会在输出 `domain` / `classical` / `ipcidr` 前统一生效。
- `rulesets`：把 `external` 来源的 `vendor/rules/` 缓存文件和 `local` 来源的 `config/rules/` 文件合并成本地 ignored `rules/*.yaml`，再发布到 `publish` 分支；`outputs` 按 `domain` / `classical` / `ipcidr` 分组，每个输出用 `file` 声明文件名，需要替换主模板已有 provider 时，在对应输出上声明 `replaces`。

数据流：

```text
config/custom.yaml:template + vendor/templates/Custom_Clash_Full.ini
  -> templates/Custom_Clash_Full_Plus.ini

config/custom.yaml:rules + vendor/rules/* + config/rules/*
  -> rules/*.yaml
```

## 规则来源

当前主要 provider：

```text
Custom_Direct = external:Aethersailor_Custom_Direct.list + local:Custom_Direct.list - remove.list
Custom_Proxy = external:Aethersailor_Custom_Proxy.list + local:Custom_Proxy.list - remove.list
Steam_CDN = external:Aethersailor_Steam_CDN.list - remove.list
Custom_Port_Direct = external:Aethersailor_Custom_Port_Direct.yaml - remove.list
External_Crypto = external:ACL4SSR_Crypto.list + external:Dler_Crypto.yaml - remove.list
```

新增外部补充分组时，需要两步：

1. 在 `config/custom.yaml` 的 `rules.rulesets` 里生成新的 `rules/*.yaml`。
2. 在 `config/custom.yaml` 的 `template.insertions` 里把这个 provider 插入主模板合适位置。

生成后的 payload 会按输入源分段写来源注释，方便追踪规则来自哪里。

如果更换主模板，例如从 Aethersailor 换成 ACL4SSR，需要同步调整 `template.source.*`、`template.provider_urls`、`template.insertions` 的锚点，以及 `rules.rulesets` 中要生成或替换的 provider 文件。

## 输出规则

- `domain`：只输出域名类规则，例如 `DOMAIN-SUFFIX` -> `'+.example.com'`。
- `classical`：只输出 IP、端口和 `AND`/`OR`/`NOT` logical rule；IP-CIDR 自动补 `no-resolve`。
- `ipcidr`：只输出 CIDR payload。

同一条规则如果出现在多个源里，按 `config/custom.yaml` 中 `rules.rulesets[].sources` 的顺序归到第一次出现的来源。

## 常用操作

改本地规则：

```powershell
uv run python tools/update_all.py
uv run pytest
git diff --check
```

改 INI 模板声明：

```powershell
uv run python tools/update_all.py
uv run pytest
git diff --check
```

刷新上游缓存：

```powershell
uv run python tools/update_all.py
uv run pytest
git diff --check
```

删除上游规则时，把规则写入 `config/rules/remove.list` 后重新生成。注意 `remove.list` 是多个 ruleset 共用的删除源。

仍然可以按需单独运行 `tools/sync_template.py`、`tools/sync_sources.py`、`tools/generate_rules.py` 或 `tools/generate_template.py`，但日常提交前默认使用 `uv run python tools/update_all.py`。

## GitHub Actions

- `Update Generated Files`：当 `config/**`、`tools/**`、`pyproject.toml` 或 `uv.lock` 被 push 时自动触发，也可手动触发。它会拉取上游内容到 ignored `vendor/` 缓存，重新生成 ignored `rules/` 和 `templates/`，通过测试后把公开产物推送到 `publish` 分支。
- `Validate`：只保留手动触发，用于需要时完整跑测试、一键生成和工作树检查。

## 本地使用

1. 使用上面的模板 URL。
2. 在本地 SubConverter-Extended 或 `api.asailor.org` 中传入订阅链接和该 INI。
3. 生成 OpenClash 可用的最终 `config.yaml`。
4. 推送或复制到 OpenClash。

## 目录

```text
config/custom.yaml          项目生成声明
config/custom.sample.yaml   配置字段样例
config/rules/               手写规则源和删除规则
vendor/                     上游同步缓存，已忽略，不提交
templates/                  本地生成的 INI 模板，已忽略；发布到 publish 分支
rules/                      本地生成的 YAML 规则集，已忽略；发布到 publish 分支
tools/                      同步和生成脚本
tests/                      规则转换和流水线测试
```
