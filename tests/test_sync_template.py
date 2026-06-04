from pathlib import Path

import pytest
import yaml

from tools.sync_template import sync_template_from_config


def test_sync_template_downloads_declared_upstream_base(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """确认 custom.yaml 的 template 段会把主模板 URL 同步到 vendor/templates 缓存。"""
    config = tmp_path / "config" / "custom.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        yaml.safe_dump(
            {
                "template": {
                    "source": {
                        "name": "ACL4SSR Online Full",
                        "upstream_url": "https://example.test/ACL4SSR_Online_Full.ini",
                        "file": "ACL4SSR_Online_Full.ini",
                    },
                    "output": "Custom_Clash_Full_Plus.ini",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    seen_urls: list[str] = []

    def fetcher(url: str) -> str:
        seen_urls.append(url)
        return "; upstream template   \r\n[custom]\r\n"

    sync_template_from_config(config, root=tmp_path, fetcher=fetcher)

    assert seen_urls == ["https://example.test/ACL4SSR_Online_Full.ini"]
    assert (tmp_path / "vendor" / "templates" / "ACL4SSR_Online_Full.ini").read_text(
        encoding="utf-8"
    ) == "; upstream template\n[custom]\n"
    assert capsys.readouterr().out.splitlines() == [
        "[同步模板] https://example.test/ACL4SSR_Online_Full.ini -> vendor/templates/ACL4SSR_Online_Full.ini"
    ]


def test_sync_template_rejects_missing_template_section(tmp_path: Path) -> None:
    """确认 custom.yaml 必须显式使用 template.source 段声明主模板。"""
    config = tmp_path / "config" / "custom.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        yaml.safe_dump(
            {
                "template": {
                    "output": "Custom_Clash_Full_Plus.ini",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="template"):
        sync_template_from_config(config, root=tmp_path, fetcher=lambda url: "; missing source\n")
