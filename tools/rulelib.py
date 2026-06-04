"""解析、过滤、去重和渲染 Clash 规则及 rule-provider payload。"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    comment: str | None = field(default=None, compare=False)

    @property
    def normalized(self) -> str:
        parts = [self.kind, self.value, *self.options]
        return ",".join(parts)


@dataclass(frozen=True, order=True)
class PayloadItem:
    value: str
    comment: str | None = field(default=None, compare=False)


PayloadEntry = str | PayloadItem


def is_local_rule_source(path: Path) -> bool:
    parts = path.as_posix().split("/")
    return any(
        parts[index : index + 2] == ["config", "rules"]
        for index in range(len(parts) - 1)
    )


def has_inline_comment(text: str) -> bool:
    for index, char in enumerate(text):
        if char == "#" and index > 0 and text[index - 1].isspace():
            return True
    return False


def parse_rule_line(
    line: str,
    path: Path,
    line_number: int,
    comment: str | None = None,
) -> Rule | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("- "):
        stripped = stripped[2:].strip()
    if not stripped or stripped in {"payload:", "payload: []"}:
        return None
    if has_inline_comment(stripped):
        raise ValueError(
            f"{path}:{line_number}: inline comments are not supported: {line.strip()}"
        )

    head, separator, tail = stripped.partition(",")
    if not separator:
        raise ValueError(f"{path}:{line_number}: invalid rule line: {line.strip()}")

    kind = head.strip().upper()
    if kind in LOGICAL_RULE_TYPES:
        expression = tail.strip()
        if not expression:
            raise ValueError(f"{path}:{line_number}: invalid rule line: {line.strip()}")
        return Rule(kind=kind, value=expression, comment=comment)

    parts = [part.strip() for part in stripped.split(",")]
    if len(parts) < 2:
        raise ValueError(f"{path}:{line_number}: invalid rule line: {line.strip()}")

    kind = parts[0].upper()
    if kind in IGNORED_RULE_TYPES:
        return None
    if kind not in CLASSICAL_RULE_TYPES:
        raise ValueError(f"{path}:{line_number}: unsupported rule type: {line.strip()}")

    return Rule(kind=kind, value=parts[1], options=tuple(part for part in parts[2:] if part), comment=comment)


def load_rules(path: Path | str) -> list[Rule]:
    rule_path = Path(path)
    rules: list[Rule] = []
    pending_comment: str | None = None
    preserve_comments = is_local_rule_source(rule_path)
    for line_number, line in enumerate(rule_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            pending_comment = None
            continue
        if stripped.startswith("##"):
            continue
        if stripped.startswith("#"):
            if preserve_comments:
                pending_comment = stripped[1:].strip() or None
            continue

        rule = parse_rule_line(
            line,
            rule_path,
            line_number,
            comment=pending_comment if preserve_comments else None,
        )
        pending_comment = None
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


def domain_payload(rules: Iterable[Rule]) -> list[PayloadItem]:
    payload: list[PayloadItem] = []
    for rule in rules:
        if rule.kind == "DOMAIN-SUFFIX":
            payload.append(PayloadItem(f"'+.{rule.value}'", rule.comment))
        elif rule.kind == "DOMAIN":
            payload.append(PayloadItem(f"'{rule.value}'", rule.comment))
    return sorted(payload)


def ipcidr_payload(rules: Iterable[Rule]) -> list[PayloadItem]:
    return sorted(
        PayloadItem(f"'{rule.value}'", rule.comment)
        for rule in rules
        if rule.kind in IPCIDR_RULE_TYPES
    )


def classical_payload(rules: Iterable[Rule]) -> list[PayloadItem]:
    payload: list[PayloadItem] = []
    for rule in rules:
        if rule.kind in {"DOMAIN", "DOMAIN-SUFFIX"}:
            continue
        if rule.kind in IPCIDR_RULE_TYPES and "no-resolve" not in rule.options:
            rule = Rule(rule.kind, rule.value, (*rule.options, "no-resolve"), comment=rule.comment)
        payload.append(PayloadItem(rule.normalized, rule.comment))
    return sorted(payload)


def payload_value(item: PayloadEntry) -> str:
    return item.value if isinstance(item, PayloadItem) else item


def payload_comment(item: PayloadEntry) -> str | None:
    return item.comment if isinstance(item, PayloadItem) else None


def render_payload_entries(payload: Iterable[PayloadEntry]) -> list[str]:
    lines: list[str] = []
    for item in payload:
        comment = payload_comment(item)
        if comment:
            lines.append(f"  # {comment}")
        lines.append(f"  - {payload_value(item)}")
    return lines


def render_payload_yaml(source: str, payload: Iterable[PayloadEntry]) -> str:
    payload_items = list(payload)
    payload_header = "payload:" if payload_items else "payload: []"
    lines = [
        f"# 生成自 {source}",
        f"# 总数: {len(payload_items)}",
        "",
        payload_header,
    ]
    lines.extend(render_payload_entries(payload_items))
    lines.append("")
    return "\n".join(lines)


def render_payload_yaml_sections(
    source: str,
    sections: Iterable[tuple[str, Iterable[PayloadEntry]]],
) -> str:
    non_empty_sections = [
        (label, payload_items)
        for label, payload in sections
        if (payload_items := list(payload))
    ]
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
        lines.extend(render_payload_entries(payload))
    lines.append("")
    return "\n".join(lines)


def write_payload_yaml(path: Path | str, source: str, payload: Iterable[PayloadEntry]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_payload_yaml(source, payload), encoding="utf-8", newline="\n")


def write_payload_yaml_sections(
    path: Path | str,
    source: str,
    sections: Iterable[tuple[str, Iterable[PayloadEntry]]],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_payload_yaml_sections(source, sections), encoding="utf-8", newline="\n")
