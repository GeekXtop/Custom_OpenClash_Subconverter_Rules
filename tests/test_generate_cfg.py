from pathlib import Path

import yaml

from tools.generate_cfg import generate_cfg_from_overlay


def test_generate_cfg_applies_replacements_and_anchor_insertions(tmp_path: Path) -> None:
    base = tmp_path / "vendor" / "cfg" / "Custom_Clash_Full.ini"
    output = tmp_path / "dist" / "cfg" / "Custom_Clash_Full_Plus.ini"
    overlay = tmp_path / "local" / "cfg" / "full-plus.yaml"
    base.parent.mkdir(parents=True)
    overlay.parent.mkdir(parents=True)
    base.write_text(
        "\n".join(
            [
                "; upstream",
                "[custom]",
                "ruleset=🎯 全球直连,clash-classic:https://testingcf.jsdelivr.net/gh/Aethersailor/Custom_OpenClash_Rules@main/rule/Custom_Direct_Classical_IP.yaml,28800",
                "ruleset=🛒 国外电商,[]GEOSITE,category-ecommerce",
                "custom_proxy_group=🌎 国外媒体`select`[]🚀 手动选择`.*",
                "enable_rule_generator=true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    overlay.write_text(
        yaml.safe_dump(
            {
                "base": "vendor/cfg/Custom_Clash_Full.ini",
                "output": "dist/cfg/Custom_Clash_Full_Plus.ini",
                "replace": [
                    {
                        "from": "Aethersailor/Custom_OpenClash_Rules",
                        "to": "GeekXtop/Custom_OpenClash_Subconverter_Rules",
                    },
                    {
                        "from": "@main/rule/",
                        "to": "@main/dist/rules/",
                    },
                    {
                        "from": "Custom_Direct_Classical_IP.yaml",
                        "to": "Custom_Direct_Classical.yaml",
                    },
                ],
                "insertions": [
                    {
                        "position": "before",
                        "anchor": "ruleset=🛒 国外电商,[]GEOSITE,category-ecommerce",
                        "lines": ["ruleset=🪙 Crypto,[]GEOSITE,category-cryptocurrency"],
                    },
                    {
                        "position": "after_prefix",
                        "anchor": "custom_proxy_group=🌎 国外媒体`",
                        "lines": ["custom_proxy_group=🪙 Crypto`select`[]🚀 手动选择`.*"],
                    },
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    generate_cfg_from_overlay(overlay, root=tmp_path)

    generated = output.read_text(encoding="utf-8")
    assert "GeekXtop/Custom_OpenClash_Subconverter_Rules" in generated
    assert "dist/rules/Custom_Direct_Classical.yaml" in generated
    assert generated.index("ruleset=🪙 Crypto") < generated.index("ruleset=🛒 国外电商")
    assert generated.index("custom_proxy_group=🌎 国外媒体") < generated.index("custom_proxy_group=🪙 Crypto")
