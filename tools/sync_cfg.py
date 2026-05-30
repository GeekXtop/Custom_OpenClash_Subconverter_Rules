from __future__ import annotations

import argparse
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.cfg_common import load_yaml, normalize_text


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "custom-openclash-cfg-sync/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def sync_cfg_from_overlay(
    overlay_path: Path | str,
    root: Path | str | None = None,
    fetcher: Callable[[str], str] = fetch_url,
) -> None:
    overlay_file = Path(overlay_path)
    overlay = load_yaml(overlay_file)
    project_root = Path(root) if root is not None else overlay_file.resolve().parents[2]

    upstream_url = overlay.get("upstream_url")
    if not upstream_url:
        raise ValueError(f"{overlay_file}: missing upstream_url")

    base_path = project_root / overlay["base"]
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(normalize_text(fetcher(upstream_url)), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync upstream INI templates declared by overlays.")
    parser.add_argument(
        "--overlay",
        default="local/cfg/full-plus.yaml",
        help="Path to the overlay YAML file.",
    )
    args = parser.parse_args()
    sync_cfg_from_overlay(Path(args.overlay))


if __name__ == "__main__":
    main()
