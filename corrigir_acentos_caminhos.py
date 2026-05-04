from pathlib import Path
import unicodedata
import re

PASTA_BASE = Path("images")
DATA_JS = Path("data.js")

def sem_acentos(texto):
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto

def limpar_nome(nome):
    nome = sem_acentos(nome)
    nome = nome.lower()
    nome = nome.replace(" ", "")
    nome = nome.replace("%c3%b4", "o")
    nome = nome.replace("%C3%B4", "o")
    nome = re.sub(r"[^a-z0-9._-]", "", nome)
    return nome

# 1. Renomeia pastas e arquivos dentro de images
for caminho in sorted(PASTA_BASE.rglob("*"), key=lambda p: len(p.parts), reverse=True):
    nome_novo = limpar_nome(caminho.name)

    if nome_novo != caminho.name:
        novo_caminho = caminho.with_name(nome_novo)

        if novo_caminho.exists():
            print(f"⚠️ Já existe, pulei: {novo_caminho}")
            continue

        print(f"Renomeando: {caminho} -> {novo_caminho}")
        caminho.rename(novo_caminho)

# 2. Corrige o data.js
if DATA_JS.exists():
    texto = DATA_JS.read_text(encoding="utf-8")

    def corrigir_url(match):
        url = match.group(0)

        partes = url.split("/")
        partes_corrigidas = [limpar_nome(parte) if "images" in partes[:i] else parte for i, parte in enumerate(partes)]

        return "/".join(partes_corrigidas)

    texto_corrigido = re.sub(
        r"https://raw\.githubusercontent\.com/[^\"]+",
        corrigir_url,
        texto
    )

    DATA_JS.write_text(texto_corrigido, encoding="utf-8")
    print("✅ data.js corrigido")
else:
    print("❌ data.js não encontrado")

print("✅ Finalizado")