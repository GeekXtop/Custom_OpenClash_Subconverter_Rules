from pathlib import Path

import yaml

from tools.sync_sources import convert_domain_list_community, sync_external_sources


def test_sync_external_sources_downloads_enabled_sources(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "external_sources": [
                    {
                        "name": "Example",
                        "enabled": True,
                        "url": "https://example.test/rules.list",
                        "output": "vendor/rules/example.list",
                    },
                    {
                        "name": "Disabled",
                        "enabled": False,
                        "url": "https://example.test/disabled.list",
                        "output": "vendor/rules/disabled.list",
                    },
                ]
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


def test_sync_external_sources_normalizes_downloaded_text(tmp_path: Path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "external_sources": [
                    {
                        "name": "Example",
                        "enabled": True,
                        "url": "https://example.test/rules.list",
                        "output": "vendor/rules/example.list",
                    },
                ]
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
