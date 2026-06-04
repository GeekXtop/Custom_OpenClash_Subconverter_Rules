# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目本质

这不是一个应用，而是一个**规则维护 / 生成流水线**。它维护公开的 `SubConverter-Extended` INI 模板（`templates/Custom_Clash_Full_Plus.ini`）和配套的 Clash rule-provider YAML（`rules/*.yaml`）。最终 `config.yaml` 由用户本地的 SubConverter-Extended 生成，**不在本仓库**；也不生成 `.mrs`。

最重要的心智模型：严格区分**源**与**生成产物**。

- **源**（手写 / 声明）：`config/custom.yaml`、`config/rules/*.list`
- **生成产物**（脚本输出，main 分支 ignored）：`rules/*.yaml`、`templates/Custom_Clash_Full_Plus.ini`
- **发布产物**（Action 提交到 `publish` 分支）：`rules/*.yaml`、`templates/Custom_Clash_Full_Plus.ini`
- **上游缓存**（脚本下载，ignored，不提交）：`vendor/templates/`、`vendor/rules/`

**永远只改源。绝不手动提交生成产物到 main**——`Update Generated Files` 会在 `config/**`、`tools/**`、`pyproject.toml` 或 `uv.lock` push 后自动重跑流水线，并把公开产物提交到 `publish` 分支；`Validate` 仅保留手动完整验证入口。

## 常用命令

```bash
# 改了任何源之后，重新同步上游并生成全部产物：
uv run python tools/update_all.py

uv run pytest                          # 全部测试
uv run pytest tests/test_rulelib.py    # 单个文件
uv run pytest tests/test_rulelib.py::test_domain_payload_converts_supported_domain_rules  # 单个测试

git status --short     # 验证产物是否最新（无输出 = 干净；有输出 = 忘了重新生成或上游已漂移）
git diff --check       # 检查行尾空格 / 冲突标记
```

仍然可以按需单独运行 `tools/sync_template.py`、`tools/generate_template.py`、`tools/sync_sources.py` 或 `tools/generate_rules.py`，但日常提交前默认使用 `uv run python tools/update_all.py`。

## 架构：一份配置，两条流水线

每条流水线都是 `sync`（拉上游内容到 ignored `vendor/` 缓存）→ `generate`（应用本地声明产出公开文件）。

### 1. INI 模板流水线（`config/custom.yaml:template`）

`config/custom.yaml` 的 `template` 段声明主模板派生逻辑；主模板可替换，不限于 Aethersailor：

- `sync_template.py` 读 `template.source.upstream_url`，按 `template.source.file` 下载主模板到固定的 ignored `vendor/templates/` 缓存目录。
- `generate_template.py` 读 `vendor/templates/<template.source.file>` 缓存，根据 `template.provider_urls` 和 `rules.rulesets[].outputs.*.replaces` 改写模板 provider URL，再应用 `template.insertions`（基于锚点的行插入，如 Crypto 代理组），按 `template.output` 写出固定的 `templates/` 发布目录。

### 2. 规则集流水线（`config/custom.yaml:rules`）

`config/custom.yaml` 的 `rules` 段声明外部规则源、手写规则源和公开 provider 输出：

- `sync_sources.py` 同步 `rules.external_sources` 中 `enabled: true` 的源到固定的 ignored `vendor/rules/` 缓存目录，每项用 `file` 声明文件名。支持 `format: domain-list-community`（v2ray domain-list 格式转换，递归展开 `include:`）。
- `generate_rules.py` 按 `rules.rulesets` 声明，对每个规则集：按顺序合并 `sources`（`external` 固定读 `vendor/rules/` 缓存，`local` 固定读 `config/rules/`）→ 去重 → 减去共享 `rules.remove`（固定读 `config/rules/`）→ 按 `outputs` 的 `domain` / `classical` / `ipcidr` 键渲染 → 按输出 `file` 写 `rules/*.yaml`。

### 核心库 `tools/rulelib.py`

规则解析、去重、删除、payload 渲染的核心。语义要点（改规则前必须知道）：

- **支持的规则类型有限**：DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD / IP-CIDR / IP-CIDR6 / SRC-PORT / DST-PORT / AND / OR / NOT。logical rule 只进入 `classical` 输出，后面的嵌套表达式原样保留；`PROCESS-NAME` 被**静默忽略**，其他未知类型**直接报错**（fail-fast）。
- 同时解析 `.list` 和 Clash `.yaml` payload 两种输入格式。
- 三种输出 `behavior`：`domain`（DOMAIN-SUFFIX→`'+.x'`，DOMAIN→`'x'`，DOMAIN-KEYWORD→`'*x*'`）、`classical`（只输出 IP-CIDR / IP-CIDR6 / SRC-PORT / DST-PORT / logical rule，并自动给 IP-CIDR 补 `no-resolve`）、`ipcidr`。
- 生成后的 payload 按输入源分段写入 `# 来源: ...` 注释；重复规则按 `rules.rulesets[].sources` 顺序归到第一次出现的来源。
- **remove 的级联语义**：用 `DOMAIN-SUFFIX,example.com` 作删除规则时，会连带删除其所有子域（`api.example.com` 等）。
- 输出始终**排序**并带稳定 header（`# 生成自` / `# 总数`），保证 diff 干净。

## 关键不变量

1. **可复现性**：发布产物必须能由源和最新上游完整重建。`.github/workflows/update-generated.yml` 在生成输入变更后同步上游、生成公开产物、运行测试，并把 `rules/` 和 `templates/` 推送到 `publish` 分支；触发输入包括 `config/**`、`tools/**`、`pyproject.toml` 和 `uv.lock`。`Validate` 只保留手动完整验证入口；`vendor/`、`rules/` 和 `templates/` 在 main 都是 ignored，不提交。
2. **强制 LF**：所有输出用 `newline="\n"` 写入。Win11 环境下注意别让编辑器把生成产物改成 CRLF。
3. **geosite 不去重**：`External_Crypto_Domain.yaml` 是对 INI 中 `GEOSITE,category-cryptocurrency` 的**补充而非替换**。生成阶段刻意不对 geosite 做去重，避免上游缓存版本与用户路由器本地 geosite 版本不一致时漏规则。
4. **`config/custom.yaml` 是项目生成声明的单一事实源**：`tests/test_project_manifest.py` 锁定了关键的源→输出映射和 External_Crypto 约束，调整配置结构时须同步更新该测试。
5. **不提交到 main**：`vendor/`、`rules/`、`templates/`、`config.yaml`、订阅链接、provider 缓存、`*.local.yaml`、`.env` 等本地私有、缓存或生成产物（见 `.gitignore`）。

更多目录约定见 `AGENTS.md` 和 `README.md`（两者均为权威说明，默认语言简体中文）。
