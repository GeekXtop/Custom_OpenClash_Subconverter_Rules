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
    print(f"[更新] 配置：{config_file}", flush=True)
    print("[更新] 1/4 同步上游模板", flush=True)
    sync_template(config_file)
    print("[更新] 2/4 同步外部规则源", flush=True)
    sync_sources(config_file)
    print("[更新] 3/4 生成 rule-provider YAML", flush=True)
    generate_rules(config_file)
    print("[更新] 4/4 生成 INI 模板", flush=True)
    generate_template(config_file)
    print("[更新] 完成", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="同步上游缓存并重新生成公开模板和规则。"
    )
    parser.add_argument("--config", default="config/custom.yaml", help="项目配置 YAML 文件路径。")
    args = parser.parse_args()
    run_update_pipeline(Path(args.config))


if __name__ == "__main__":
    main()
