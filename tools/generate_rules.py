from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.rulelib import (
    apply_remove_rules,
    classical_payload,
    domain_payload,
    ipcidr_payload,
    load_rules,
    unique_rules,
    write_payload_yaml,
)


def load_manifest(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a mapping")
    return data


def payload_for_behavior(behavior: str, rules: list) -> list[str]:
    if behavior == "domain":
        return domain_payload(rules)
    if behavior == "ipcidr":
        return ipcidr_payload(rules)
    if behavior == "classical":
        return classical_payload(rules)
    raise ValueError(f"unsupported output behavior: {behavior}")


def generate_from_manifest(manifest_path: Path | str, root: Path | str | None = None) -> None:
    manifest = load_manifest(Path(manifest_path))
    project_root = Path(root) if root is not None else Path(manifest_path).resolve().parent

    for ruleset in manifest.get("rulesets", []):
        sources = ruleset.get("sources", [])
        if not sources:
            raise ValueError(f"{ruleset.get('name', '<unnamed>')}: ruleset must declare sources")

        rules = []
        for source in sources:
            rules.extend(load_rules(project_root / source))
        rules = unique_rules(rules)

        remove_rules = []
        for remove_source in ruleset.get("remove", []):
            remove_rules.extend(load_rules(project_root / remove_source))
        if remove_rules:
            rules = apply_remove_rules(rules, unique_rules(remove_rules))

        source_label = ", ".join(sources)
        for output in ruleset.get("outputs", []):
            behavior = output["behavior"]
            output_path = project_root / output["path"]
            write_payload_yaml(output_path, source_label, payload_for_behavior(behavior, rules))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate public Clash rule-provider YAML files.")
    parser.add_argument("--manifest", default="sources.yaml", help="Path to sources.yaml")
    args = parser.parse_args()
    generate_from_manifest(Path(args.manifest))


if __name__ == "__main__":
    main()
