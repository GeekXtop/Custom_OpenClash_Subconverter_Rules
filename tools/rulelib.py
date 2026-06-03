"""解析、过滤、去重和渲染 Clash 规则及 rule-provider payload。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DOMAIN_RULE_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
IPCIDR_RULE_TYPES = {"IP-CIDR", "IP-CIDR6"}
LOGICAL_RULE_TYPES = {"AND", "OR", "NOT"}
CLASSICAL_RULE_TYPES = DOMAIN_RULE_TYPES | IPCIDR_RULE_TYPES | {"SRC-PORT", "DST-PORT"} | LOGICAL_RULE_TYPES
IGNORED_RULE_TYPES = {"PROCESS-NAME"}


@dataclass(frozen=True, order=True)
class Rule:
    kind: str
    value: str
    options: tuple[str, ...] = ()

    @property
    def normalized(self) -> str:
        parts = [self.kind, self.value, *self.options]
        return ",".join(parts)


def parse_rule_line(line: str, path: Path, line_number: int) -> Rule | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped in {"payload:", "payload: []"}:
        return None
    if stripped.startswith("- "):
        stripped = stripped[2:].strip()

    head, separator, tail = stripped.partition(",")
    if not separator:
        raise ValueError(f"{path}:{line_number}: invalid rule line: {line.strip()}")

    kind = head.strip().upper()
    if kind in LOGICAL_RULE_TYPES:
        expression = tail.strip()
        if not expression:
            raise ValueError(f"{path}:{line_number}: invalid rule line: {line.strip()}")
        return Rule(kind=kind, value=expression)

    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) < 2:
        raise ValueError(f"{path}:{line_number}: invalid rule line: {line.strip()}")

    kind = parts[0].upper()
    if kind in IGNORED_RULE_TYPES:
        return None
    if kind not in CLASSICAL_RULE_TYPES:
        raise ValueError(f"{path}:{line_number}: unsupported rule type: {line.strip()}")

    return Rule(kind=kind, value=parts[1], options=tuple(part for part in parts[2:] if part))


def load_rules(path: Path | str) -> list[Rule]:
    rule_path = Path(path)
    rules: list[Rule] = []
    for line_number, line in enumerate(rule_path.read_text(encoding="utf-8").splitlines(), start=1):
        rule = parse_rule_line(line, rule_path, line_number)
        if rule is not None:
            rules.append(rule)
    return unique_rules(rules)


def unique_rules(rules: Iterable[Rule]) -> list[Rule]:
    seen: set[str] = set()
    unique: list[Rule] = []
    for rule in rules:
        key = rule.normalized
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)
    return unique


def apply_remove_rules(rules: Iterable[Rule], remove_rules: Iterable[Rule]) -> list[Rule]:
    remove = list(remove_rules)
    return [rule for rule in rules if not is_removed(rule, remove)]


def is_removed(rule: Rule, remove_rules: Iterable[Rule]) -> bool:
    for remove_rule in remove_rules:
        if rule.normalized == remove_rule.normalized:
            return True
        if remove_rule.kind == "DOMAIN-SUFFIX" and rule.kind in {"DOMAIN", "DOMAIN-SUFFIX"}:
            if rule.value == remove_rule.value or rule.value.endswith(f".{remove_rule.value}"):
                return True
    return False


def domain_payload(rules: Iterable[Rule]) -> list[str]:
    payload: list[str] = []
    for rule in rules:
        if rule.kind == "DOMAIN-SUFFIX":
            payload.append(f"'+.{rule.value}'")
        elif rule.kind == "DOMAIN":
            payload.append(f"'{rule.value}'")
        elif rule.kind == "DOMAIN-KEYWORD":
            payload.append(f"'*{rule.value}*'")
    return sorted(payload)


def ipcidr_payload(rules: Iterable[Rule]) -> list[str]:
    return sorted(f"'{rule.value}'" for rule in rules if rule.kind in IPCIDR_RULE_TYPES)


def classical_payload(rules: Iterable[Rule]) -> list[str]:
    payload: list[str] = []
    for rule in rules:
        if rule.kind in DOMAIN_RULE_TYPES:
            continue
        if rule.kind in IPCIDR_RULE_TYPES and "no-resolve" not in rule.options:
            rule = Rule(rule.kind, rule.value, (*rule.options, "no-resolve"))
        payload.append(rule.normalized)
    return sorted(payload)


def render_payload_yaml(source: str, payload: list[str]) -> str:
    payload_header = "payload:" if payload else "payload: []"
    lines = [
        f"# 生成自 {source}",
        f"# 总数: {len(payload)}",
        "",
        payload_header,
    ]
    lines.extend(f"  - {item}" for item in payload)
    lines.append("")
    return "\n".join(lines)


def render_payload_yaml_sections(source: str, sections: Iterable[tuple[str, list[str]]]) -> str:
    non_empty_sections = [(label, payload) for label, payload in sections if payload]
    total = sum(len(payload) for _, payload in non_empty_sections)
    if not non_empty_sections:
        return render_payload_yaml(source, [])

    lines = [
        f"# 生成自 {source}",
        f"# 总数: {total}",
        "",
        "payload:",
    ]
    for label, payload in non_empty_sections:
        lines.append(f"  # 来源: {label}")
        lines.extend(f"  - {item}" for item in payload)
    lines.append("")
    return "\n".join(lines)


def write_payload_yaml(path: Path | str, source: str, payload: list[str]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_payload_yaml(source, payload), encoding="utf-8", newline="\n")


def write_payload_yaml_sections(
    path: Path | str,
    source: str,
    sections: Iterable[tuple[str, list[str]]],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_payload_yaml_sections(source, sections), encoding="utf-8", newline="\n")
