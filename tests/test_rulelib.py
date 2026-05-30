from pathlib import Path

import pytest

from tools.rulelib import (
    Rule,
    apply_remove_rules,
    domain_payload,
    ipcidr_payload,
    load_rules,
    render_payload_yaml,
)


def test_load_rules_skips_comments_and_rejects_invalid_lines(tmp_path: Path) -> None:
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


def test_load_rules_ignores_process_name_rules(tmp_path: Path) -> None:
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


def test_domain_payload_converts_supported_domain_rules() -> None:
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
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",)),
        Rule("IP-CIDR6", "2001:db8::/32", ("no-resolve",)),
    ]

    assert ipcidr_payload(rules) == ["'192.0.2.0/24'", "'2001:db8::/32'"]


def test_apply_remove_rules_removes_normalized_entries() -> None:
    rules = [
        Rule("DOMAIN-SUFFIX", "example.com"),
        Rule("DOMAIN-SUFFIX", "other.test"),
    ]
    remove = [Rule("DOMAIN-SUFFIX", "example.com")]

    assert apply_remove_rules(rules, remove) == [Rule("DOMAIN-SUFFIX", "other.test")]


def test_apply_remove_rules_removes_domains_covered_by_suffix() -> None:
    rules = [
        Rule("DOMAIN-SUFFIX", "wallet.example.com"),
        Rule("DOMAIN", "api.example.com"),
        Rule("DOMAIN-SUFFIX", "other.test"),
    ]
    remove = [Rule("DOMAIN-SUFFIX", "example.com")]

    assert apply_remove_rules(rules, remove) == [Rule("DOMAIN-SUFFIX", "other.test")]


def test_render_payload_yaml_includes_stable_header_and_payload() -> None:
    text = render_payload_yaml(
        source="local/rules/custom.list",
        payload=["'+.example.com'", "'exact.example.com'"],
    )

    assert text == "\n".join(
        [
            "# 生成自 local/rules/custom.list",
            "# 总数: 2",
            "",
            "payload:",
            "  - '+.example.com'",
            "  - 'exact.example.com'",
            "",
        ]
    )
