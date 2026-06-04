from pathlib import Path

import yaml

PUBLISH_TRIGGER_PATHS = [
    "config/**",
    "tools/**",
    ".github/workflows/**",
    "pyproject.toml",
    "uv.lock",
]


def load_workflow(path: str) -> dict:
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_validate_workflow_is_manual_only() -> None:
    """确认 Validate 不阻塞 config 提交，只保留手动验证入口。"""
    workflow = load_workflow(".github/workflows/validate.yml")
    triggers = workflow["on"]

    assert set(triggers) == {"workflow_dispatch"}


def test_update_generated_workflow_auto_runs_for_generation_inputs() -> None:
    """确认影响生成结果的输入变化会触发发布产物更新。"""
    workflow = load_workflow(".github/workflows/update-generated.yml")
    triggers = workflow["on"]
    step_scripts = "\n".join(
        step.get("run", "")
        for step in workflow["jobs"]["update-generated"]["steps"]
    )

    assert triggers["push"]["paths"] == PUBLISH_TRIGGER_PATHS
    assert "workflow_dispatch" in triggers
    assert "git rm -rf --ignore-unmatch ." in step_scripts
    assert "git rm -r --ignore-unmatch ." not in step_scripts
    assert "git clean -fdx" in step_scripts
    assert "git push origin publish" in step_scripts


def test_readme_lists_publish_urls() -> None:
    """确认 README 明确记录最终发布 URL。"""
    readme = Path("README.md").read_text(encoding="utf-8")

    assert (
        "https://raw.githubusercontent.com/GeekXtop/Custom_OpenClash_Subconverter_Rules/publish/templates/Custom_Clash_Full_Plus.ini"
        in readme
    )
    assert (
        "https://raw.githubusercontent.com/GeekXtop/Custom_OpenClash_Subconverter_Rules/publish/rules/"
        in readme
    )
