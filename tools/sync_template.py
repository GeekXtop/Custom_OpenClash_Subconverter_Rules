"""下载 config/custom.yaml 声明的上游 INI 模板并写入 vendor/templates 缓存。"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.config_common import (
    load_yaml,
    normalize_text,
    project_root_for_config,
    template_section,
    template_source_path,
    template_source_upstream_url,
)


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "custom-openclash-template-sync/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def sync_template_from_config(
    config_path: Path | str,
    root: Path | str | None = None,
    fetcher: Callable[[str], str] = fetch_url,
) -> None:
    config_file = Path(config_path)
    template_config = template_section(load_yaml(config_file))
    project_root = Path(root) if root is not None else project_root_for_config(config_file)

    upstream_url = template_source_upstream_url(template_config)
    base_path = project_root / template_source_path(template_config)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(normalize_text(fetcher(upstream_url)), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync upstream INI templates declared in config/custom.yaml.")
    parser.add_argument(
        "--config",
        default="config/custom.yaml",
        help="Path to the project config YAML file.",
    )
    args = parser.parse_args()
    sync_template_from_config(Path(args.config))


if __name__ == "__main__":
    main()
