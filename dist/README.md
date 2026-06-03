# 发布产物

此目录包含生成后的公开文件:

- `templates/Custom_Clash_Full_Plus.ini`: SubConverter-Extended INI 模板。
- `rules/*.yaml`: Clash rule-provider YAML。

不要直接编辑这些文件。请编辑 `config/custom.yaml`、`config/rules/` 或对应脚本，然后运行:

```powershell
uv run python tools/generate_template.py
uv run python tools/generate_rules.py
```
