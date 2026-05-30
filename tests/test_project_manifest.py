from pathlib import Path

import yaml


def test_external_crypto_does_not_dedupe_against_geosite() -> None:
    manifest = yaml.safe_load(Path("sources.yaml").read_text(encoding="utf-8"))

    external_source_names = {source["name"] for source in manifest["external_sources"]}
    assert "Geosite_Category_Cryptocurrency" not in external_source_names

    external_crypto = next(
        ruleset for ruleset in manifest["rulesets"] if ruleset["name"] == "External_Crypto"
    )
    assert external_crypto["sources"] == [
        "vendor/rules/ACL4SSR_Crypto.list",
        "vendor/rules/Dler_Crypto.yaml",
    ]
    assert external_crypto["remove"] == ["local/rules/remove.list"]


def test_aethersailor_rules_are_external_base_sources() -> None:
    manifest = yaml.safe_load(Path("sources.yaml").read_text(encoding="utf-8"))

    external_outputs = {source["name"]: source["output"] for source in manifest["external_sources"]}
    assert external_outputs["Aethersailor_Custom_Direct"] == "vendor/rules/Aethersailor_Custom_Direct.list"
    assert external_outputs["Aethersailor_Custom_Proxy"] == "vendor/rules/Aethersailor_Custom_Proxy.list"
    assert external_outputs["Aethersailor_Steam_CDN"] == "vendor/rules/Aethersailor_Steam_CDN.list"
    assert external_outputs["Aethersailor_Custom_Port_Direct"] == (
        "vendor/rules/Aethersailor_Custom_Port_Direct.yaml"
    )

    rulesets = {ruleset["name"]: ruleset for ruleset in manifest["rulesets"]}
    assert rulesets["Custom_Direct"]["sources"] == [
        "vendor/rules/Aethersailor_Custom_Direct.list",
        "local/rules/Custom_Direct.list",
    ]
    assert rulesets["Custom_Proxy"]["sources"] == [
        "vendor/rules/Aethersailor_Custom_Proxy.list",
        "local/rules/Custom_Proxy.list",
    ]
    assert rulesets["Steam_CDN"]["sources"] == ["vendor/rules/Aethersailor_Steam_CDN.list"]
    assert rulesets["Custom_Port_Direct"]["sources"] == [
        "vendor/rules/Aethersailor_Custom_Port_Direct.yaml"
    ]


def test_generated_outputs_are_under_dist() -> None:
    manifest = yaml.safe_load(Path("sources.yaml").read_text(encoding="utf-8"))

    output_paths = [
        output["path"]
        for ruleset in manifest["rulesets"]
        for output in ruleset["outputs"]
    ]

    assert output_paths
    assert all(path.startswith("dist/rules/") for path in output_paths)
