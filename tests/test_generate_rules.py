from pathlib import Path

import yaml

from tools.generate_rules import generate_from_manifest


def test_generate_from_manifest_writes_declared_outputs(tmp_path: Path) -> None:
    """确认 custom.yaml 的 rules 段能驱动规则合并、去重、删除、分来源输出。"""
    base_source = tmp_path / "vendor" / "rules" / "base.list"
    source = tmp_path / "config" / "rules" / "custom.list"
    remove = tmp_path / "config" / "rules" / "remove.list"
    base_source.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    base_source.write_text(
        "\n".join(
            [
                "DOMAIN-SUFFIX,remove.example.com",
                "DOMAIN-SUFFIX,keep.example.com",
                "DOMAIN-SUFFIX,duplicate.example.com",
                "DST-PORT,8443",
            ]
        ),
        encoding="utf-8",
    )
    source.write_text(
        "\n".join(
            [
                "DOMAIN-SUFFIX,duplicate.example.com",
                "DOMAIN-SUFFIX,local.example.com",
                "IP-CIDR,192.0.2.0/24,no-resolve",
            ]
        ),
        encoding="utf-8",
    )
    remove.write_text("DOMAIN-SUFFIX,remove.example.com\n", encoding="utf-8")

    manifest = tmp_path / "config" / "custom.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "rules": {
                    "remove": ["remove.list"],
                    "rulesets": [
                        {
                            "name": "Custom_Test",
                            "sources": [
                                {"external": "base.list"},
                                {"local": "custom.list"},
                            ],
                            "outputs": {
                                "domain": {"file": "Custom_Test_Domain.yaml"},
                                "ipcidr": {"file": "Custom_Test_IP.yaml"},
                                "classical": {"file": "Custom_Test_Classical.yaml"},
                            },
                        }
                    ]
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    generate_from_manifest(manifest, root=tmp_path)

    assert (tmp_path / "dist" / "rules" / "Custom_Test_Domain.yaml").read_text(
        encoding="utf-8"
    ) == "\n".join(
        [
            "# 生成自 vendor/rules/base.list, config/rules/custom.list",
            "# 总数: 3",
            "",
            "payload:",
            "  # 来源: vendor/rules/base.list",
            "  - '+.duplicate.example.com'",
            "  - '+.keep.example.com'",
            "  # 来源: config/rules/custom.list",
            "  - '+.local.example.com'",
            "",
        ]
    )
    assert "'192.0.2.0/24'" in (tmp_path / "dist" / "rules" / "Custom_Test_IP.yaml").read_text(
        encoding="utf-8"
    )
    classical = (tmp_path / "dist" / "rules" / "Custom_Test_Classical.yaml").read_text(
        encoding="utf-8"
    )
    assert "  # 来源: vendor/rules/base.list" in classical
    assert "  # 来源: config/rules/custom.list" in classical
    assert "  - DST-PORT,8443" in classical
    assert "keep.example.com" not in classical
    assert "remove.example.com" not in classical
