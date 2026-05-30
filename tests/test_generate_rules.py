from pathlib import Path

import yaml

from tools.generate_rules import generate_from_manifest


def test_generate_from_manifest_writes_declared_outputs(tmp_path: Path) -> None:
    source = tmp_path / "local" / "rules" / "custom.list"
    remove = tmp_path / "local" / "rules" / "remove.list"
    source.parent.mkdir(parents=True)
    source.write_text(
        "\n".join(
            [
                "DOMAIN-SUFFIX,remove.example.com",
                "DOMAIN-SUFFIX,keep.example.com",
                "IP-CIDR,192.0.2.0/24,no-resolve",
                "DST-PORT,8443",
            ]
        ),
        encoding="utf-8",
    )
    remove.write_text("DOMAIN-SUFFIX,remove.example.com\n", encoding="utf-8")

    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "rulesets": [
                    {
                        "name": "Custom_Test",
                        "sources": ["local/rules/custom.list"],
                        "remove": ["local/rules/remove.list"],
                        "outputs": [
                            {"behavior": "domain", "path": "dist/rules/Custom_Test_Domain.yaml"},
                            {"behavior": "ipcidr", "path": "dist/rules/Custom_Test_IP.yaml"},
                            {"behavior": "classical", "path": "dist/rules/Custom_Test_Classical.yaml"},
                        ],
                    }
                ]
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
            "# 生成自 local/rules/custom.list",
            "# 总数: 1",
            "",
            "payload:",
            "  - '+.keep.example.com'",
            "",
        ]
    )
    assert "'192.0.2.0/24'" in (tmp_path / "dist" / "rules" / "Custom_Test_IP.yaml").read_text(
        encoding="utf-8"
    )
    classical = (tmp_path / "dist" / "rules" / "Custom_Test_Classical.yaml").read_text(
        encoding="utf-8"
    )
    assert "  - DST-PORT,8443" in classical
    assert "remove.example.com" not in classical
