import re
import requests
from collections import defaultdict

# abre o data.js
with open("data.js", "r", encoding="utf-8") as f:
    text = f.read()

# pega todas as URLs de imagem
urls = re.findall(r'https://raw\.githubusercontent\.com[^"]+', text)

faltando = []
por_marca = defaultdict(int)

print(f"🔎 Verificando {len(urls)} imagens...\n")

for i, url in enumerate(urls):
    try:
        r = requests.head(url)
        if r.status_code != 200:
            faltando.append(url)

            # extrai marca do caminho
            partes = url.split("/")
            if len(partes) > 9:
                marca = partes[9]
                por_marca[marca] += 1

        if i % 200 == 0:
            print(f"Processadas: {i}")

    except:
        faltando.append(url)

print("\n❌ IMAGENS FALTANDO:")
for url in faltando[:100]:
    print(url)

if len(faltando) > 100:
    print(f"... e mais {len(faltando)-100}")

print("\n📊 FALTANDO POR MARCA:")
for marca, qtd in sorted(por_marca.items(), key=lambda x: -x[1]):
    print(f"{marca}: {qtd}")

print(f"\n🔥 TOTAL QUEBRADAS: {len(faltando)}")