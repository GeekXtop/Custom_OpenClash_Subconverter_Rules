"""根据 config/custom.yaml 的 template 段生成发布用 SubConverter-Extended INI 模板。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.config_common import (
    load_yaml,
    normalize_text,
    project_root_for_config,
    rule_output_path,
    rules_section,
    ruleset_outputs,
    template_output_path,
    template_section,
    template_source_path,
)


def apply_replacements(text: str, replacements: list[dict[str, str]]) -> str:
    result = text
    for replacement in replacements:
        result = result.replace(replacement["from"], replacement["to"])
    return result


def _join_url(base: str, filename: str) -> str:
    return f"{base.rstrip('/')}/{filename.lstrip('/')}"


def provider_replacements(template_config: dict, rules: dict) -> list[dict[str, str]]:
    provider_urls = template_config.get("provider_urls")
    replacements: list[dict[str, str]] = []

    for ruleset in rules.get("rulesets", []):
        for _behavior, output in ruleset_outputs(ruleset):
            template_provider = output.get("replaces")
            if template_provider is None:
                continue
            if not isinstance(template_provider, str) or not template_provider:
                raise ValueError(f"{ruleset.get('name', '<unnamed>')}: replaces must be a string")
            if not isinstance(provider_urls, dict):
                raise ValueError(
                    "template.provider_urls must be a mapping when outputs replace template providers"
                )

            upstream_base = provider_urls.get("upstream_base")
            publish_base = provider_urls.get("publish_base")
            if not isinstance(upstream_base, str) or not upstream_base:
                raise ValueError("template.provider_urls.upstream_base is required")
            if not isinstance(publish_base, str) or not publish_base:
                raise ValueError("template.provider_urls.publish_base is required")

            output_path = rule_output_path(output)

            replacements.append(
                {
                    "from": _join_url(upstream_base, template_provider),
                    "to": _join_url(publish_base, Path(output_path).name),
                }
            )

    return replacements


def find_anchor_index(lines: list[str], insertion: dict) -> int:
    anchor = insertion["anchor"]
    position = insertion["position"]
    for index, line in enumerate(lines):
        if position == "after_prefix":
            if line.startswith(anchor):
                return index
        elif line == anchor:
            return index
    raise ValueError(f"anchor not found: {anchor}")


def apply_insertions(text: str, insertions: list[dict]) -> str:
    lines = text.splitlines()
    for insertion in insertions:
        index = find_anchor_index(lines, insertion)
        new_lines = insertion["lines"]
        position = insertion["position"]
        if position == "before":
            insert_at = index
        elif position in {"after", "after_prefix"}:
            insert_at = index + 1
        else:
            raise ValueError(f"unsupported insertion position: {position}")
        lines[insert_at:insert_at] = new_lines
    return "\n".join(lines) + "\n"


def generate_template_from_config(config_path: Path | str, root: Path | str | None = None) -> None:
    config_file = Path(config_path)
    config = load_yaml(config_file)
    template_config = template_section(config)
    rules = rules_section(config)
    project_root = Path(root) if root is not None else project_root_for_config(config_file)

    base_path = project_root / template_source_path(template_config)
    output_path = project_root / template_output_path(template_config)
    text = normalize_text(base_path.read_text(encoding="utf-8"))
    text = apply_replacements(text, provider_replacements(template_config, rules))
    text = apply_insertions(text, template_config.get("insertions", []))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate INI templates from config/custom.yaml.")
    parser.add_argument(
        "--config",
        default="config/custom.yaml",
        help="Path to the project config YAML file.",
    )
    args = parser.parse_args()
    generate_template_from_config(Path(args.config))


if __name__ == "__main__":
    main()
