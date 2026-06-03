"""项目配置 YAML 读取、分段校验与文本规范化工具。"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import yaml

VENDOR_TEMPLATE_DIR = Path("vendor/templates")
PUBLISH_TEMPLATE_DIR = Path("templates")
VENDOR_RULES_DIR = Path("vendor/rules")
CONFIG_RULES_DIR = Path("config/rules")
PUBLISH_RULES_DIR = Path("rules")


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping")
    return data


def project_root_for_config(config_file: Path) -> Path:
    return config_file.resolve().parents[1]


def file_name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} is required")
    if (
        "/" in value
        or "\\" in value
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or PureWindowsPath(value).drive
        or value in {".", ".."}
    ):
        raise ValueError(f"{field} must be a file name, not a path")
    return value


def path_text(path: Path) -> str:
    return path.as_posix()


def template_section(config: dict[str, Any]) -> dict[str, Any]:
    template = config.get("template")
    if not isinstance(template, dict):
        raise ValueError("template must be a mapping")
    return template


def rules_section(config: dict[str, Any]) -> dict[str, Any]:
    rules = config.get("rules")
    if not isinstance(rules, dict):
        raise ValueError("rules must be a mapping")
    return rules


def ruleset_outputs(ruleset: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    outputs = ruleset.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError(f"{ruleset.get('name', '<unnamed>')}: outputs must be a mapping")

    normalized_outputs = []
    for behavior, output in outputs.items():
        if not isinstance(behavior, str) or not behavior:
            raise ValueError(f"{ruleset.get('name', '<unnamed>')}: output behavior must be a string")
        if not isinstance(output, dict):
            raise ValueError(f"{ruleset.get('name', '<unnamed>')}.{behavior}: output must be a mapping")
        normalized_outputs.append((behavior, output))
    return normalized_outputs


def template_source(template_config: dict[str, Any]) -> dict[str, Any]:
    source = template_config.get("source")
    if not isinstance(source, dict):
        raise ValueError("template.source must be a mapping")
    return source


def template_source_path(template_config: dict[str, Any]) -> Path:
    source = template_source(template_config)
    return VENDOR_TEMPLATE_DIR / file_name(source.get("file"), "template.source.file")


def template_output_path(template_config: dict[str, Any]) -> Path:
    return PUBLISH_TEMPLATE_DIR / file_name(template_config.get("output"), "template.output")


def template_source_upstream_url(template_config: dict[str, Any]) -> str:
    source = template_source(template_config)
    upstream_url = source.get("upstream_url")
    if not isinstance(upstream_url, str) or not upstream_url:
        raise ValueError("template.source upstream_url is required")
    return upstream_url


def external_source_path(source: dict[str, Any]) -> Path:
    return VENDOR_RULES_DIR / file_name(source.get("file"), "rules.external_sources[].file")


def remove_source_path(remove_source: Any) -> Path:
    return CONFIG_RULES_DIR / file_name(remove_source, "rules.remove[]")


def ruleset_source_path(source: Any, ruleset_name: str) -> Path:
    if not isinstance(source, dict) or len(source) != 1:
        raise ValueError(f"{ruleset_name}: source must be {{external: file}} or {{local: file}}")

    source_type, source_file = next(iter(source.items()))
    if source_type == "external":
        return VENDOR_RULES_DIR / file_name(source_file, f"{ruleset_name}.sources[].external")
    if source_type == "local":
        return CONFIG_RULES_DIR / file_name(source_file, f"{ruleset_name}.sources[].local")
    raise ValueError(f"{ruleset_name}: unsupported source type: {source_type}")


def rule_output_path(output: dict[str, Any]) -> Path:
    return PUBLISH_RULES_DIR / file_name(output.get("file"), "rulesets.outputs.*.file")


def normalize_text(content: str) -> str:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return "\n".join(line.rstrip() for line in lines) + "\n"
