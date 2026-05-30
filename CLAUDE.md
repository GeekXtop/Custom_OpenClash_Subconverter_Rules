# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目本质

这不是一个应用，而是一个**规则维护 / 生成流水线**。它维护公开的 `SubConverter-Extended` INI 模板（`dist/cfg/Custom_Clash_Full_Plus.ini`）和配套的 Clash rule-provider YAML（`dist/rules/*.yaml`）。最终 `config.yaml` 由用户本地的 SubConverter-Extended 生成，**不在本仓库**；也不生成 `.mrs`。

最重要的心智模型：严格区分**源**与**生成产物**。

- **源**（手写 / 声明）：`local/rules/*.list`、`sources.yaml`、`local/cfg/full-plus.yaml`
- **生成产物**（脚本输出，已提交到 git）：`dist/rules/*.yaml`、`dist/cfg/Custom_Clash_Full_Plus.ini`、`vendor/cfg/`、`vendor/rules/`

**永远只改源，然后重新生成。绝不手动编辑生成产物**——CI 会重跑整条流水线并用 `git diff` 验证产物与源一致。

## 常用命令

```bash
# 改了任何源之后，重新生成全部产物（两条流水线相互独立，sync 须在 generate 之前）：
uv run python tools/sync_cfg.py        # 拉上游 INI 快照
uv run python tools/generate_cfg.py    # 应用 overlay 生成公开 INI
uv run python tools/sync_sources.py    # 拉外部规则源快照
uv run python tools/generate_rules.py  # 生成 dist/rules/*.yaml

uv run pytest                          # 全部测试
uv run pytest tests/test_rulelib.py    # 单个文件
uv run pytest tests/test_rulelib.py::test_domain_payload_converts_supported_domain_rules  # 单个测试

git diff --exit-code   # 验证产物是否最新（CI 等价检查，有 diff = 忘了重新生成或上游已漂移）
git diff --check       # 检查行尾空格 / 冲突标记
```

## 架构：两条声明驱动的流水线

每条流水线都是 `sync`（拉上游快照）→ `generate`（应用本地声明产出公开文件）。

### 1. INI 模板流水线（`cfg/`）

`local/cfg/full-plus.yaml` 是唯一声明文件，同时驱动两步：

- `sync_cfg.py` 读其 `upstream_url`，下载 Aethersailor 的 `Custom_Clash_Full.ini` 到 `base`（`vendor/cfg/` 快照）。
- `generate_cfg.py` 读 `base` 快照，应用 `replace`（文本替换：仓库路径、规则文件名）和 `insertions`（基于锚点的行插入，如 Crypto 代理组），写出 `dist/cfg/Custom_Clash_Full_Plus.ini`。

### 2. 规则集流水线（`local/` + `vendor/` → `dist/rules/`）

`sources.yaml` 是唯一声明文件，含两段：

- `sync_sources.py` 同步 `external_sources` 中 `enabled: true` 的源到 `vendor/rules/`。支持 `format: domain-list-community`（v2ray domain-list 格式转换，递归展开 `include:`）。
- `generate_rules.py` 按 `rulesets` 声明，对每个规则集：合并 `sources`（external + local）→ 去重 → 减去 `remove`（`local/rules/remove.list`）→ 按 `behavior` 渲染 → 写 `dist/rules/*.yaml`。

### 核心库 `tools/rulelib.py`

规则解析、去重、删除、payload 渲染的核心。语义要点（改规则前必须知道）：

- **支持的规则类型有限**：DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD / IP-CIDR / IP-CIDR6 / SRC-PORT / DST-PORT。`PROCESS-NAME` 被**静默忽略**，其他未知类型**直接报错**（fail-fast）。
- 同时解析 `.list` 和 Clash `.yaml` payload 两种输入格式。
- 三种输出 `behavior`：`domain`（DOMAIN-SUFFIX→`'+.x'`，DOMAIN→`'x'`，DOMAIN-KEYWORD→`'*x*'`）、`classical`（自动给 IP-CIDR 补 `no-resolve`）、`ipcidr`。
- **remove 的级联语义**：用 `DOMAIN-SUFFIX,example.com` 作删除规则时，会连带删除其所有子域（`api.example.com` 等）。
- 输出始终**排序**并带稳定 header（`# 生成自` / `# 总数`），保证 diff 干净。

## 关键不变量

1. **可复现性**：生成产物必须能由源完整重建并已提交。`.github/workflows/validate.yml` 重跑整条流水线后用 `git diff --exit-code` 校验。注意 sync 步骤会拉**最新上游**——上游漂移会让 CI 变红，此时需在本地重新 sync 并提交更新后的快照与产物。
2. **强制 LF**：所有输出用 `newline="\n"` 写入。Win11 环境下注意别让编辑器把生成产物改成 CRLF。
3. **geosite 不去重**：`External_Crypto_Domain.yaml` 是对 INI 中 `GEOSITE,category-cryptocurrency` 的**补充而非替换**。生成阶段刻意不对 geosite 做去重，避免本仓库快照与用户路由器本地 geosite 版本不一致时漏规则。
4. **`sources.yaml` 是规则集的单一事实源**：`tests/test_project_manifest.py` 锁定了关键的源→输出映射和 External_Crypto 约束，调整 `sources.yaml` 结构时须同步更新该测试。
5. **不提交**：`config.yaml`、订阅链接、provider 缓存、`*.local.yaml`、`.env` 等本地私有产物（见 `.gitignore`）。

更多目录约定见 `AGENTS.md` 和 `README.md`（两者均为权威说明，默认语言简体中文）。
