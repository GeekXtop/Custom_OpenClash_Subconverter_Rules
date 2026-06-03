"""一键同步上游缓存并重新生成公开模板和规则集。"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.generate_rules import generate_from_manifest
from tools.generate_template import generate_template_from_config
from tools.sync_sources import sync_external_sources
from tools.sync_template import sync_template_from_config


PipelineStep = Callable[[Path], None]


def run_update_pipeline(
    config_path: Path | str,
    sync_template: PipelineStep = sync_template_from_config,
    sync_sources: PipelineStep = sync_external_sources,
    generate_rules: PipelineStep = generate_from_manifest,
    generate_template: PipelineStep = generate_template_from_config,
) -> None:
    config_file = Path(config_path)
    sync_template(config_file)
    sync_sources(config_file)
    generate_rules(config_file)
    generate_template(config_file)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync upstream cache and regenerate public templates/rules."
    )
    parser.add_argument("--config", default="config/custom.yaml", help="Path to the project config YAML file.")
    args = parser.parse_args()
    run_update_pipeline(Path(args.config))


if __name__ == "__main__":
    main()
