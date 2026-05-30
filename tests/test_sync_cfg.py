from pathlib import Path

import yaml

from tools.sync_cfg import sync_cfg_from_overlay


def test_sync_cfg_downloads_declared_upstream_base(tmp_path: Path) -> None:
    overlay = tmp_path / "local" / "cfg" / "full-plus.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        yaml.safe_dump(
            {
                "upstream_url": "https://example.test/Custom_Clash_Full.ini",
                "base": "vendor/cfg/Custom_Clash_Full.ini",
                "output": "dist/cfg/Custom_Clash_Full_Plus.ini",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    seen_urls: list[str] = []

    def fetcher(url: str) -> str:
        seen_urls.append(url)
        return "; upstream template   \r\n[custom]\r\n"

    sync_cfg_from_overlay(overlay, root=tmp_path, fetcher=fetcher)

    assert seen_urls == ["https://example.test/Custom_Clash_Full.ini"]
    assert (tmp_path / "vendor" / "cfg" / "Custom_Clash_Full.ini").read_text(
        encoding="utf-8"
    ) == "; upstream template\n[custom]\n"
