"""根据 config/custom.yaml 的 rules 段合并规则源并生成公开 Clash rule-provider YAML。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.config_common import (
    load_yaml,
    path_text,
    project_root_for_config,
    remove_source_path,
    rule_output_path,
    rules_section,
    ruleset_outputs,
    ruleset_source_path,
)
from tools.rulelib import (
    PayloadItem,
    apply_remove_rules,
    classical_payload,
    domain_payload,
    ipcidr_payload,
    load_rules,
    unique_rules,
    write_payload_yaml_sections,
)


def payload_for_behavior(behavior: str, rules: list) -> list[PayloadItem]:
    if behavior == "domain":
        return domain_payload(rules)
    if behavior == "ipcidr":
        return ipcidr_payload(rules)
    if behavior == "classical":
        return classical_payload(rules)
    raise ValueError(f"unsupported output behavior: {behavior}")


def load_source_sections(project_root: Path, ruleset_name: str, sources: list) -> list[tuple[str, list]]:
    seen: set[str] = set()
    sections = []
    for source in sources:
        source_path = ruleset_source_path(source, ruleset_name)
        source_label = path_text(source_path)
        rules = []
        for rule in load_rules(project_root / source_path):
            if rule.normalized in seen:
                continue
            seen.add(rule.normalized)
            rules.append(rule)
        sections.append((source_label, rules))
    return sections


def generate_from_manifest(manifest_path: Path | str, root: Path | str | None = None) -> None:
    manifest_file = Path(manifest_path)
    manifest = rules_section(load_yaml(manifest_file))
    project_root = Path(root) if root is not None else project_root_for_config(manifest_file)

    remove_sources = manifest.get("remove", [])
    if not isinstance(remove_sources, list):
        raise ValueError("rules.remove must be a list")

    remove_rules = []
    for remove_source in remove_sources:
        remove_rules.extend(load_rules(project_root / remove_source_path(remove_source)))
    unique_remove_rules = unique_rules(remove_rules) if remove_rules else []

    for ruleset in manifest.get("rulesets", []):
        ruleset_name = ruleset.get("name", "<unnamed>")
        sources = ruleset.get("sources", [])
        if not sources:
            raise ValueError(f"{ruleset_name}: ruleset must declare sources")

        source_sections = load_source_sections(project_root, ruleset_name, sources)

        if unique_remove_rules:
            source_sections = [
                (source, apply_remove_rules(rules, unique_remove_rules))
                for source, rules in source_sections
            ]

        source_label = ", ".join(source for source, _rules in source_sections)
        for behavior, output in ruleset_outputs(ruleset):
            output_path = project_root / rule_output_path(output)
            sections = [
                (source, payload_for_behavior(behavior, rules))
                for source, rules in source_sections
            ]
            write_payload_yaml_sections(output_path, source_label, sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate public Clash rule-provider YAML files.")
    parser.add_argument("--config", default="config/custom.yaml", help="Path to the project config YAML file.")
    args = parser.parse_args()
    generate_from_manifest(Path(args.config))


if __name__ == "__main__":
    main()
