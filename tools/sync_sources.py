from __future__ import annotations

import argparse
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_manifest(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a mapping")
    return data


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "custom-openclash-rule-sync/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def normalize_text(content: str) -> str:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(line.rstrip() for line in lines) + "\n"


def convert_domain_list_community(
    content: str,
    base_url: str,
    fetcher: Callable[[str], str] = fetch_url,
    seen_includes: set[str] | None = None,
) -> str:
    seen = set() if seen_includes is None else seen_includes
    rules: list[str] = []

    for raw_line in content.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        token = line.split()[0]
        if token.startswith("include:"):
            include_name = token.split(":", 1)[1]
            if include_name in seen:
                continue
            seen.add(include_name)
            include_url = urllib.parse.urljoin(base_url.rsplit("/", 1)[0] + "/", include_name)
            included = convert_domain_list_community(
                fetcher(include_url),
                base_url=include_url,
                fetcher=fetcher,
                seen_includes=seen,
            )
            rules.extend(rule for rule in included.splitlines() if rule)
            continue

        if token.startswith("full:"):
            rules.append(f"DOMAIN,{token.split(':', 1)[1]}")
        elif token.startswith("keyword:"):
            rules.append(f"DOMAIN-KEYWORD,{token.split(':', 1)[1]}")
        elif token.startswith("domain:"):
            rules.append(f"DOMAIN-SUFFIX,{token.split(':', 1)[1]}")
        elif ":" in token:
            rules.append(f"# [UNSUPPORTED] {token}")
        else:
            rules.append(f"DOMAIN-SUFFIX,{token}")

    return "\n".join(rules) + "\n"


def content_for_source(source: dict[str, Any], fetcher: Callable[[str], str]) -> str:
    normalized = normalize_text(fetcher(source["url"]))
    if source.get("format") == "domain-list-community":
        return convert_domain_list_community(normalized, base_url=source["url"], fetcher=fetcher)
    return normalized


def sync_external_sources(
    manifest_path: Path | str,
    root: Path | str | None = None,
    fetcher: Callable[[str], str] = fetch_url,
) -> None:
    manifest = load_manifest(Path(manifest_path))
    project_root = Path(root) if root is not None else Path(manifest_path).resolve().parent

    for source in manifest.get("external_sources", []):
        if not source.get("enabled", False):
            continue

        url = source["url"]
        output_path = project_root / source["output"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content_for_source(source, fetcher), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download enabled external rule sources.")
    parser.add_argument("--manifest", default="sources.yaml", help="Path to sources.yaml")
    args = parser.parse_args()
    sync_external_sources(Path(args.manifest))


if __name__ == "__main__":
    main()
