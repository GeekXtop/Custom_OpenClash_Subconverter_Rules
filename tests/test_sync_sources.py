from pathlib import Path

import pytest
import yaml

from tools.sync_sources import convert_domain_list_community, sync_external_sources


def test_sync_external_sources_downloads_enabled_sources(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """确认只同步 external_sources 中 enabled=true 的外部规则源。"""
    manifest = tmp_path / "config" / "custom.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "rules": {
                    "external_sources": [
                        {
                            "name": "Example",
                            "enabled": True,
                            "url": "https://example.test/rules.list",
                            "file": "example.list",
                        },
                        {
                            "name": "Disabled",
                            "enabled": False,
                            "url": "https://example.test/disabled.list",
                            "file": "disabled.list",
                        },
                    ]
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    seen_urls: list[str] = []

    def fetcher(url: str) -> str:
        seen_urls.append(url)
        return "DOMAIN-SUFFIX,example.com\n"

    sync_external_sources(manifest, root=tmp_path, fetcher=fetcher)

    assert seen_urls == ["https://example.test/rules.list"]
    assert (tmp_path / "vendor" / "rules" / "example.list").read_text(encoding="utf-8") == (
        "DOMAIN-SUFFIX,example.com\n"
    )
    assert not (tmp_path / "vendor" / "rules" / "disabled.list").exists()
    assert capsys.readouterr().out.splitlines() == [
        "[同步规则源] Example：https://example.test/rules.list -> vendor/rules/example.list",
        "[同步规则源] 完成：1 个文件",
    ]


def test_sync_external_sources_normalizes_downloaded_text(tmp_path: Path) -> None:
    """确认下载到 vendor/rules 的外部规则会统一行尾并去掉行尾空白。"""
    manifest = tmp_path / "config" / "custom.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "rules": {
                    "external_sources": [
                        {
                            "name": "Example",
                            "enabled": True,
                            "url": "https://example.test/rules.list",
                            "file": "example.list",
                        },
                    ]
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def fetcher(url: str) -> str:
        return "DOMAIN-SUFFIX,example.com   \r\n   \r\nDOMAIN-SUFFIX,test.example.com\t\r\n"

    sync_external_sources(manifest, root=tmp_path, fetcher=fetcher)

    assert (tmp_path / "vendor" / "rules" / "example.list").read_text(encoding="utf-8") == (
        "DOMAIN-SUFFIX,example.com\n\nDOMAIN-SUFFIX,test.example.com\n"
    )


def test_convert_domain_list_community_converts_and_expands_includes() -> None:
    """确认 v2fly domain-list-community 格式会转换并递归展开 include。"""
    fetched: list[str] = []

    def fetcher(url: str) -> str:
        fetched.append(url)
        return "included.example.com\nfull:exact-included.example.com\n"

    converted = convert_domain_list_community(
        "\n".join(
            [
                "# 注释",
                "include:included",
                "full:exact.example.com @cn",
                "keyword:wallet",
                "domain.example.com",
                "regexp:^unsupported$",
            ]
        ),
        base_url="https://example.test/data/category",
        fetcher=fetcher,
    )

    assert fetched == ["https://example.test/data/included"]
    assert converted == "\n".join(
        [
            "DOMAIN-SUFFIX,included.example.com",
            "DOMAIN,exact-included.example.com",
            "DOMAIN,exact.example.com",
            "DOMAIN-KEYWORD,wallet",
            "DOMAIN-SUFFIX,domain.example.com",
            "# [UNSUPPORTED] regexp:^unsupported$",
            "",
        ]
    )
