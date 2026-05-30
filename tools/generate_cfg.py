from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.cfg_common import load_yaml, normalize_text


def apply_replacements(text: str, replacements: list[dict[str, str]]) -> str:
    result = text
    for replacement in replacements:
        result = result.replace(replacement["from"], replacement["to"])
    return result


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


def generate_cfg_from_overlay(overlay_path: Path | str, root: Path | str | None = None) -> None:
    overlay_file = Path(overlay_path)
    overlay = load_yaml(overlay_file)
    project_root = Path(root) if root is not None else overlay_file.resolve().parents[2]

    base_path = project_root / overlay["base"]
    output_path = project_root / overlay["output"]
    text = normalize_text(base_path.read_text(encoding="utf-8"))
    text = apply_replacements(text, overlay.get("replace", []))
    text = apply_insertions(text, overlay.get("insertions", []))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate INI templates from upstream bases and overlays.")
    parser.add_argument(
        "--overlay",
        default="local/cfg/full-plus.yaml",
        help="Path to the overlay YAML file.",
    )
    args = parser.parse_args()
    generate_cfg_from_overlay(Path(args.overlay))


if __name__ == "__main__":
    main()
