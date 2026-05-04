import json
import re
from pathlib import Path

ARQUIVO_ORIGINAL = Path("data.js")
ARQUIVO_NOVO = Path("data_cloud.js")

CLOUD_NAME = "dz3uocw2h"
PASTA_CLOUDINARY = "arquivo-desfiles"

def carregar_data_js(caminho):
    texto = caminho.read_text(encoding="utf-8")
    texto = re.sub(r"^\s*const\s+data\s*=\s*", "", texto)
    texto = re.sub(r";\s*$", "", texto)
    return json.loads(texto)

def salvar_data_js(caminho, data):
    conteudo = "const data = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    caminho.write_text(conteudo, encoding="utf-8")

data = carregar_data_js(ARQUIVO_ORIGINAL)

for item in data:
    imagem = item.get("image", "")

    if imagem.startswith("images/"):
        caminho_sem_images = imagem.replace("images/", "", 1)
        item["image"] = (
            f"https://res.cloudinary.com/{CLOUD_NAME}/image/upload/"
            f"{PASTA_CLOUDINARY}/{caminho_sem_images}"
        )

salvar_data_js(ARQUIVO_NOVO, data)

print(f"Pronto: {ARQUIVO_NOVO} criado.")
print(f"Total de itens: {len(data)}")