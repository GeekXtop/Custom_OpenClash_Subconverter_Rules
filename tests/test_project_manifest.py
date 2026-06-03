from pathlib import Path

import yaml


def test_ini_template_config_uses_file_names() -> None:
    """确认 INI 模板配置只声明文件名，固定目录由脚本约束。"""
    template = yaml.safe_load(Path("config/custom.yaml").read_text(encoding="utf-8"))["template"]

    assert template["source"]["file"] == "Custom_Clash_Full.ini"
    assert template["output"] == "Custom_Clash_Full_Plus.ini"


def test_template_provider_rewrites_are_declared_on_ruleset_outputs() -> None:
    """确认模板 provider 替换由 rules 输出声明。"""
    manifest = yaml.safe_load(Path("config/custom.yaml").read_text(encoding="utf-8"))
    template = manifest["template"]
    rulesets = {
        ruleset["name"]: {
            output["file"]: output
            for output in ruleset["outputs"].values()
        }
        for ruleset in manifest["rules"]["rulesets"]
    }

    assert template["provider_urls"] == {
        "upstream_base": "https://testingcf.jsdelivr.net/gh/Aethersailor/Custom_OpenClash_Rules@main/rule/",
        "publish_base": "https://testingcf.jsdelivr.net/gh/GeekXtop/Custom_OpenClash_Subconverter_Rules@main/dist/rules/",
    }
    assert rulesets["Custom_Direct"]["Custom_Direct_Domain.yaml"][
        "replaces"
    ] == "Custom_Direct_Domain.yaml"
    assert rulesets["Custom_Direct"]["Custom_Direct_Classical.yaml"][
        "replaces"
    ] == "Custom_Direct_Classical_IP.yaml"
    assert rulesets["Custom_Proxy"]["Custom_Proxy_Domain.yaml"][
        "replaces"
    ] == "Custom_Proxy_Domain.yaml"
    assert rulesets["Custom_Proxy"]["Custom_Proxy_Classical.yaml"][
        "replaces"
    ] == "Custom_Proxy_Classical_IP.yaml"
    assert rulesets["Steam_CDN"]["Steam_CDN_Classical.yaml"][
        "replaces"
    ] == "Steam_CDN_Classical.yaml"
    assert rulesets["Custom_Port_Direct"]["Custom_Port_Direct.yaml"][
        "replaces"
    ] == "Custom_Port_Direct.yaml"


def test_external_crypto_does_not_dedupe_against_geosite() -> None:
    """确认 External_Crypto 只补充外部源，不试图和运行时 geosite 去重。"""
    manifest = yaml.safe_load(Path("config/custom.yaml").read_text(encoding="utf-8"))["rules"]

    external_source_names = {source["name"] for source in manifest["external_sources"]}
    assert "Geosite_Category_Cryptocurrency" not in external_source_names

    external_crypto = next(
        ruleset for ruleset in manifest["rulesets"] if ruleset["name"] == "External_Crypto"
    )
    assert external_crypto["sources"] == [
        {"external": "ACL4SSR_Crypto.list"},
        {"external": "Dler_Crypto.yaml"},
    ]
    assert manifest["remove"] == ["remove.list"]
    assert "remove" not in external_crypto


def test_aethersailor_rules_are_external_base_sources() -> None:
    """确认 Aethersailor 上游仍是 Direct/Proxy/Steam/端口规则的基础源。"""
    manifest = yaml.safe_load(Path("config/custom.yaml").read_text(encoding="utf-8"))["rules"]

    external_outputs = {source["name"]: source["file"] for source in manifest["external_sources"]}
    assert external_outputs["Aethersailor_Custom_Direct"] == "Aethersailor_Custom_Direct.list"
    assert external_outputs["Aethersailor_Custom_Proxy"] == "Aethersailor_Custom_Proxy.list"
    assert external_outputs["Aethersailor_Steam_CDN"] == "Aethersailor_Steam_CDN.list"
    assert external_outputs["Aethersailor_Custom_Port_Direct"] == "Aethersailor_Custom_Port_Direct.yaml"

    rulesets = {ruleset["name"]: ruleset for ruleset in manifest["rulesets"]}
    assert all("remove" not in ruleset for ruleset in rulesets.values())
    assert rulesets["Custom_Direct"]["sources"] == [
        {"external": "Aethersailor_Custom_Direct.list"},
        {"local": "Custom_Direct.list"},
    ]
    assert rulesets["Custom_Proxy"]["sources"] == [
        {"external": "Aethersailor_Custom_Proxy.list"},
        {"local": "Custom_Proxy.list"},
    ]
    assert rulesets["Steam_CDN"]["sources"] == [{"external": "Aethersailor_Steam_CDN.list"}]
    assert rulesets["Custom_Port_Direct"]["sources"] == [
        {"external": "Aethersailor_Custom_Port_Direct.yaml"}
    ]


def test_generated_outputs_are_file_names() -> None:
    """确认公开 rule-provider 输出只声明文件名，固定写入 dist/rules。"""
    manifest = yaml.safe_load(Path("config/custom.yaml").read_text(encoding="utf-8"))["rules"]

    output_files = [
        output["file"]
        for ruleset in manifest["rulesets"]
        for output in ruleset["outputs"].values()
    ]

    assert output_files
    assert all("/" not in file and "\\" not in file for file in output_files)


def test_custom_sample_covers_supported_config_fields() -> None:
    """确认配置样例覆盖当前脚本支持的字段，避免文档样例过期。"""
    sample = yaml.safe_load(Path("config/custom.sample.yaml").read_text(encoding="utf-8"))

    assert set(sample) == {"template", "rules"}
    assert set(sample["template"]) == {"source", "output", "provider_urls", "insertions"}
    assert set(sample["template"]["source"]) == {"name", "upstream_url", "file"}
    assert set(sample["template"]["provider_urls"]) == {"upstream_base", "publish_base"}
    assert {insertion["position"] for insertion in sample["template"]["insertions"]} == {
        "before",
        "after",
        "after_prefix",
    }

    assert set(sample["rules"]) == {"external_sources", "remove", "rulesets"}
    external_sources = sample["rules"]["external_sources"]
    assert {"name", "enabled", "url", "file"}.issubset(external_sources[0])
    assert any(source.get("format") == "domain-list-community" for source in external_sources)

    outputs = sample["rules"]["rulesets"][0]["outputs"]
    assert set(outputs) == {"domain", "classical", "ipcidr"}
    assert all("file" in output for output in outputs.values())
    assert all("replaces" in output for output in outputs.values())
