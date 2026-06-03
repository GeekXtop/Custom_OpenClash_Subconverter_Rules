from pathlib import Path

import pytest

from tools.rulelib import (
    Rule,
    apply_remove_rules,
    classical_payload,
    domain_payload,
    ipcidr_payload,
    load_rules,
    render_payload_yaml,
    render_payload_yaml_sections,
)


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
    assert classical_payload(rules) == [
        "AND,((SRC-IP-CIDR,10.0.0.3/32),(SRC-PORT,25862))"
    ]


def test_classical_payload_excludes_domain_rules() -> None:
    """确认 classical 输出只保留 domain provider 表达不了的规则。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
        Rule("DOMAIN-KEYWORD", "keyword"),
        Rule("IP-CIDR", "192.0.2.0/24"),
        Rule("DST-PORT", "8443"),
    ]

    assert classical_payload(rules) == [
        "DST-PORT,8443",
        "IP-CIDR,192.0.2.0/24,no-resolve",
    ]


def test_domain_payload_converts_supported_domain_rules() -> None:
    """确认 domain 输出会把 Clash 域名规则转换成 domain provider 格式。"""
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN", "exact.example.com"),
        Rule("DOMAIN-KEYWORD", "wallet"),
        Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",)),
    ]

    assert domain_payload(rules) == [
        "'*wallet*'",
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

    assert ipcidr_payload(rules) == ["'192.0.2.0/24'", "'2001:db8::/32'"]


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
