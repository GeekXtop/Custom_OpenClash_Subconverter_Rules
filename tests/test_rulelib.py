from pathlib import Path

import pytest

from tools.rulelib import (
    PayloadItem,
    Rule,
    apply_remove_rules,
    classical_payload,
    domain_payload,
    ipcidr_payload,
    load_rules,
    render_payload_yaml,
    render_payload_yaml_sections,
)


def payload_values(payload: list[PayloadItem]) -> list[str]:
    return [item.value for item in payload]


def test_load_rules_skips_comments_and_rejects_invalid_lines(tmp_path: Path) -> None:
    """确认规则加载会跳过注释，并对缺少类型前缀的行 fail-fast。"""
    source = tmp_path / "rules.list"
    source.write_text(
        "\n".join(
            [
                "# 注释",
                "DOMAIN-SUFFIX,example.com",
                "plain.example.com",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="plain.example.com"):
        load_rules(source)


def test_load_rules_accepts_yaml_payload_files(tmp_path: Path) -> None:
    """确认可直接读取 Clash rule-provider YAML 的 payload 列表。"""
    source = tmp_path / "rules.yaml"
    source.write_text(
        "\n".join(
            [
                "payload:",
                "  # 注释",
                "  - DOMAIN-SUFFIX,example.com",
                "  - DOMAIN,exact.example.com",
            ]
        ),
        encoding="utf-8",
    )

    assert load_rules(source) == [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
    ]


def test_load_rules_preserves_preceding_rule_comments_for_local_rules(tmp_path: Path) -> None:
    """确认 config/rules 中单 # 注释会绑定到下一条规则，## 和空行不会进入产物。"""
    source = tmp_path / "config" / "rules" / "rules.list"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "## 文件说明不应进入生成产物",
                "# Example suffix",
                "DOMAIN-SUFFIX,example.com",
                "# 空行会清空这个注释",
                "",
                "DOMAIN,exact.example.com",
            ]
        ),
        encoding="utf-8",
    )

    rules = load_rules(source)

    assert rules == [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
    ]
    assert [rule.comment for rule in rules] == ["Example suffix", None]


def test_load_rules_ignores_rule_comments_outside_local_rules(tmp_path: Path) -> None:
    """确认 vendor 等外部规则源里的单 # 注释不会被带入生成结果。"""
    source = tmp_path / "vendor" / "rules" / "rules.list"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "# Upstream comment",
                "DOMAIN-SUFFIX,example.com",
            ]
        ),
        encoding="utf-8",
    )

    rules = load_rules(source)

    assert rules == [Rule("DOMAIN-SUFFIX", "example.com")]
    assert rules[0].comment is None


def test_load_rules_rejects_inline_rule_comments(tmp_path: Path) -> None:
    """确认行尾注释不再被支持，避免把注释静默解析成规则内容。"""
    source = tmp_path / "config" / "rules" / "rules.list"
    source.parent.mkdir(parents=True)
    source.write_text("DOMAIN-SUFFIX,example.com # Example suffix\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inline comments"):
        load_rules(source)


def test_load_rules_accepts_empty_yaml_payload_files(tmp_path: Path) -> None:
    """确认空 YAML payload 会被当作空规则集处理。"""
    source = tmp_path / "rules.yaml"
    source.write_text("payload: []\n", encoding="utf-8")

    assert load_rules(source) == []


def test_load_rules_ignores_process_name_rules(tmp_path: Path) -> None:
    """确认 PROCESS-NAME 规则会被静默忽略，不进入生成产物。"""
    source = tmp_path / "rules.list"
    source.write_text(
        "\n".join(
            [
                "PROCESS-NAME,Binance.exe",
                "DOMAIN-SUFFIX,binance.com",
            ]
        ),
        encoding="utf-8",
    )

    assert load_rules(source) == [Rule("DOMAIN-SUFFIX", "binance.com")]


def test_logical_rules_are_preserved_for_classical_payload(tmp_path: Path) -> None:
    """确认 AND/OR/NOT 这类 logical rule 会原样进入 classical payload。"""
    source = tmp_path / "rules.list"
    source.write_text(
        "AND,((SRC-IP-CIDR,10.0.0.3/32),(SRC-PORT,25862))",
        encoding="utf-8",
    )

    rules = load_rules(source)

    assert rules == [Rule("AND", "((SRC-IP-CIDR,10.0.0.3/32),(SRC-PORT,25862))")]
    assert domain_payload(rules) == []
    assert ipcidr_payload(rules) == []
    assert payload_values(classical_payload(rules)) == [
        "AND,((SRC-IP-CIDR,10.0.0.3/32),(SRC-PORT,25862))"
    ]


def test_classical_payload_excludes_domain_exact_and_suffix_rules() -> None:
    """确认 classical 输出排除 exact/suffix 域名规则，但保留 keyword 兜底。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
        Rule("DOMAIN-KEYWORD", "keyword"),
        Rule("IP-CIDR", "192.0.2.0/24"),
        Rule("DST-PORT", "8443"),
    ]

    assert payload_values(classical_payload(rules)) == [
        "DOMAIN-KEYWORD,keyword",
        "DST-PORT,8443",
        "IP-CIDR,192.0.2.0/24,no-resolve",
    ]


def test_classical_payload_keeps_domain_keyword_rules_as_fallback() -> None:
    """确认 DOMAIN-KEYWORD 会进入 classical provider，避免 domain 通配符不生效时漏匹配。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
        Rule("DOMAIN-KEYWORD", "cloudflare"),
    ]

    assert payload_values(classical_payload(rules)) == [
        "DOMAIN-KEYWORD,cloudflare",
    ]


def test_domain_payload_converts_exact_and_suffix_rules_only() -> None:
    """确认 domain 输出只包含 exact/suffix 规则，keyword 留给 classical provider。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
        Rule("DOMAIN-KEYWORD", "wallet"),
        Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",)),
    ]

    assert payload_values(domain_payload(rules)) == [
        "'+.example.com'",
        "'exact.example.com'",
    ]


def test_ipcidr_payload_keeps_only_ip_rules() -> None:
    """确认 ipcidr 输出只包含 IPv4/IPv6 CIDR 规则。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",)),
        Rule("IP-CIDR6", "2001:db8::/32", ("no-resolve",)),
    ]

    assert payload_values(ipcidr_payload(rules)) == [
        "'192.0.2.0/24'",
        "'2001:db8::/32'",
    ]


def test_apply_remove_rules_removes_normalized_entries() -> None:
    """确认 remove.list 中完全相同的规范化规则会删除源规则。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN-SUFFIX", "other.test"),
    ]
    remove = [Rule("DOMAIN-SUFFIX", "example.com")]

    assert apply_remove_rules(rules, remove) == [Rule("DOMAIN-SUFFIX", "other.test")]


def test_apply_remove_rules_removes_domains_covered_by_suffix() -> None:
    """确认 DOMAIN-SUFFIX 删除规则会级联删除其覆盖的精确域名和子域。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "wallet.example.com"),
        Rule("DOMAIN", "api.example.com"),
        Rule("DOMAIN-SUFFIX", "other.test"),
    ]
    remove = [Rule("DOMAIN-SUFFIX", "example.com")]

    assert apply_remove_rules(rules, remove) == [Rule("DOMAIN-SUFFIX", "other.test")]


def test_render_payload_yaml_includes_stable_header_and_payload() -> None:
    """确认普通 payload 渲染会输出稳定 header 和规则列表。"""
    text = render_payload_yaml(
        source="config/rules/custom.list",
        payload=["'+.example.com'", "'exact.example.com'"],
    )

    assert text == "\n".join(
        [
            "# 生成自 config/rules/custom.list",
            "# 总数: 2",
            "",
            "payload:",
            "  - '+.example.com'",
            "  - 'exact.example.com'",
            "",
        ]
    )


def test_render_payload_yaml_includes_rule_comments() -> None:
    """确认规则注释会跟随转换后的 payload 条目输出。"""
    payload = domain_payload(
        [
            Rule("DOMAIN-SUFFIX", "example.com", comment="Example suffix"),
            Rule("DOMAIN", "exact.example.com"),
        ]
    )

    text = render_payload_yaml(source="config/rules/custom.list", payload=payload)

    assert text == "\n".join(
        [
            "# 生成自 config/rules/custom.list",
            "# 总数: 2",
            "",
            "payload:",
            "  # Example suffix",
            "  - '+.example.com'",
            "  - 'exact.example.com'",
            "",
        ]
    )


def test_render_payload_yaml_renders_empty_payload_as_list() -> None:
    """确认空 payload 渲染为合法的 YAML 空列表。"""
    text = render_payload_yaml(source="config/rules/custom.list", payload=[])

    assert text == "\n".join(
        [
            "# 生成自 config/rules/custom.list",
            "# 总数: 0",
            "",
            "payload: []",
            "",
        ]
    )


def test_render_payload_yaml_sections_includes_source_comments() -> None:
    """确认按来源分段渲染时会给每段 payload 加来源注释。"""
    text = render_payload_yaml_sections(
        source="vendor/rules/base.list, config/rules/custom.list",
        sections=[
            ("vendor/rules/base.list", ["'+.base.example.com'"]),
            ("config/rules/custom.list", ["'+.local.example.com'"]),
        ],
    )

    assert text == "\n".join(
        [
            "# 生成自 vendor/rules/base.list, config/rules/custom.list",
            "# 总数: 2",
            "",
            "payload:",
            "  # 来源: vendor/rules/base.list",
            "  - '+.base.example.com'",
            "  # 来源: config/rules/custom.list",
            "  - '+.local.example.com'",
            "",
        ]
    )


def test_render_payload_yaml_sections_omits_empty_sections() -> None:
    """确认没有实际规则的来源分段不会输出空注释块。"""
    text = render_payload_yaml_sections(
        source="vendor/rules/base.list, config/rules/custom.list",
        sections=[
            ("vendor/rules/base.list", []),
            ("config/rules/custom.list", ["DST-PORT,8443"]),
        ],
    )

    assert "来源: vendor/rules/base.list" not in text
    assert "  # 来源: config/rules/custom.list" in text
