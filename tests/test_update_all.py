from pathlib import Path
import subprocess
import sys

import pytest


def test_run_update_pipeline_executes_all_steps_in_order(tmp_path: Path) -> None:
    """确认一键更新入口按固定顺序执行同步与生成步骤。"""
    try:
        from tools.update_all import run_update_pipeline
    except ModuleNotFoundError:
        pytest.fail("tools.update_all should expose run_update_pipeline")

    config = tmp_path / "config" / "custom.yaml"
    calls: list[tuple[str, Path]] = []

    run_update_pipeline(
        config,
        sync_template=lambda path: calls.append(("sync_template", path)),
        sync_sources=lambda path: calls.append(("sync_sources", path)),
        generate_rules=lambda path: calls.append(("generate_rules", path)),
        generate_template=lambda path: calls.append(("generate_template", path)),
    )

    assert calls == [
        ("sync_template", config),
        ("sync_sources", config),
        ("generate_rules", config),
        ("generate_template", config),
    ]


def test_update_all_script_can_run_as_file() -> None:
    """确认一键脚本和现有 tools/*.py 一样支持直接按文件路径运行。"""
    result = subprocess.run(
        [sys.executable, "tools/update_all.py", "--help"],
        capture_output=True,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Sync upstream cache" in result.stdout
