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


def test_run_update_pipeline_logs_steps_in_order(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """确认一键更新入口会输出阶段日志，便于本地和 CI 判断执行进度。"""
    from tools.update_all import run_update_pipeline

    config = tmp_path / "config" / "custom.yaml"

    run_update_pipeline(
        config,
        sync_template=lambda _path: None,
        sync_sources=lambda _path: None,
        generate_rules=lambda _path: None,
        generate_template=lambda _path: None,
    )

    assert capsys.readouterr().out.splitlines() == [
        f"[更新] 配置：{config}",
        "[更新] 1/4 同步上游模板",
        "[更新] 2/4 同步外部规则源",
        "[更新] 3/4 生成 rule-provider YAML",
        "[更新] 4/4 生成 INI 模板",
        "[更新] 完成",
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
    assert "同步上游缓存" in result.stdout
