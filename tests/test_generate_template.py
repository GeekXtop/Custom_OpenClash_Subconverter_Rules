from pathlib import Path

import pytest
import yaml

from tools.generate_template import generate_template_from_config


def test_generate_template_rewrites_declared_providers_and_anchor_insertions(tmp_path: Path) -> None:
    """确认 template.provider_urls 会按 rules 输出声明改写模板 provider，并按锚点插入内容。"""
    base = tmp_path / "vendor" / "templates" / "ACL4SSR_Online_Full.ini"
    output = tmp_path / "templates" / "Custom_Clash_Full_Plus.ini"
    config = tmp_path / "config" / "custom.yaml"
    base.parent.mkdir(parents=True)
    config.parent.mkdir(parents=True)
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
    config.write_text(
        yaml.safe_dump(
            {
                "template": {
                    "source": {
                        "name": "ACL4SSR Online Full",
                        "file": "ACL4SSR_Online_Full.ini",
                    },
                    "output": "Custom_Clash_Full_Plus.ini",
                    "provider_urls": {
                        "upstream_base": "https://testingcf.jsdelivr.net/gh/Aethersailor/Custom_OpenClash_Rules@main/rule/",
                        "publish_base": "https://testingcf.jsdelivr.net/gh/GeekXtop/Custom_OpenClash_Subconverter_Rules@main/rules/",
                    },
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
                "rules": {
                    "rulesets": [
                        {
                            "name": "Custom_Direct",
                            "sources": [{"external": "base.list"}],
                            "outputs": {
                                "classical": {
                                    "file": "Custom_Direct_Classical.yaml",
                                    "replaces": "Custom_Direct_Classical_IP.yaml",
                                },
                            },
                        },
                    ],
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    generate_template_from_config(config, root=tmp_path)

    generated = output.read_text(encoding="utf-8")
    assert "GeekXtop/Custom_OpenClash_Subconverter_Rules" in generated
    assert "rules/Custom_Direct_Classical.yaml" in generated
    assert generated.index("ruleset=🪙 Crypto") < generated.index("ruleset=🛒 国外电商")
    assert generated.index("custom_proxy_group=🌎 国外媒体") < generated.index("custom_proxy_group=🪙 Crypto")


def test_generate_template_requires_provider_urls_when_outputs_replace_template_provider(tmp_path: Path) -> None:
    """确认输出声明 replaces 时必须配置 provider URL 前缀。"""
    base = tmp_path / "vendor" / "templates" / "base.ini"
    config = tmp_path / "config" / "custom.yaml"
    base.parent.mkdir(parents=True)
    config.parent.mkdir(parents=True)
    base.write_text("[custom]\n", encoding="utf-8")
    config.write_text(
        yaml.safe_dump(
            {
                "template": {
                    "source": {"file": "base.ini"},
                    "output": "out.ini",
                },
                "rules": {
                    "rulesets": [
                        {
                            "name": "Needs_Provider_Urls",
                            "sources": [{"external": "base.list"}],
                            "outputs": {
                                "domain": {
                                    "file": "out.yaml",
                                    "replaces": "Template_Provider.yaml",
                                },
                            },
                        },
                    ],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provider_urls"):
        generate_template_from_config(config, root=tmp_path)
