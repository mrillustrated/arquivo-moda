from pathlib import Path
import json

arquivo = Path("data.js")

# lê o data.js
texto = arquivo.read_text(encoding="utf-8")

# transforma em objeto Python
dados = eval(texto.replace("const data =", "").strip().rstrip(";"))

for item in dados:
    ano = str(item.get("ano", "")).strip()

    if not ano:
        continue

    tags = item.get("tags", [])

    if ano not in tags:
        tags.append(ano)

    item["tags"] = tags

# salva de volta
novo = "const data = " + json.dumps(dados, indent=2, ensure_ascii=False) + ";"
arquivo.write_text(novo, encoding="utf-8")

print("Ano adicionado como tag em todos os itens")