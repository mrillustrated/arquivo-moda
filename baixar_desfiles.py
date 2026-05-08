import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path

PASTA_SAIDA = Path("downloads_desfiles")
PASTA_SAIDA.mkdir(exist_ok=True)

def limpar_nome(texto):
    texto = texto.lower().strip()
    texto = re.sub(r"https?://", "", texto)
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")[:80]

def baixar_imagem(url, pasta, numero):
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return False

        content_type = r.headers.get("content-type", "")
        if "image" not in content_type:
            return False

        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"

        nome = f"look{numero:02d}{ext}"
        caminho = pasta / nome

        with open(caminho, "wb") as f:
            f.write(r.content)

        print(f"✅ {nome}")
        return True

    except Exception as e:
        print(f"❌ Erro ao baixar {url}: {e}")
        return False

def extrair_imagens(link):
    print(f"\n🔎 Lendo: {link}")

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(link, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    urls = []

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src:
            urls.append(urljoin(link, src))

        srcset = img.get("srcset")
        if srcset:
            partes = srcset.split(",")
            for parte in partes:
                url = parte.strip().split(" ")[0]
                if url:
                    urls.append(urljoin(link, url))

    urls_limpas = []
    vistos = set()

    for u in urls:
        if u not in vistos:
            vistos.add(u)
            urls_limpas.append(u)

    return urls_limpas

def baixar_link(link):
    nome_pasta = limpar_nome(urlparse(link).path or link)
    if not nome_pasta:
        nome_pasta = limpar_nome(link)

    pasta = PASTA_SAIDA / nome_pasta
    pasta.mkdir(exist_ok=True)

    imagens = extrair_imagens(link)

    print(f"🖼️ Encontradas: {len(imagens)} imagens")
    print(f"📁 Pasta: {pasta}")

    contador = 1

    for img_url in imagens:
        ok = baixar_imagem(img_url, pasta, contador)
        if ok:
            contador += 1

    print(f"✅ Finalizado: {contador - 1} imagens baixadas em {pasta}")

def main():
    print("Cole vários links, um por linha.")
    print("Quando terminar, aperte ENTER numa linha vazia.\n")

    links = []

    while True:
        link = input("Link: ").strip()
        if not link:
            break
        links.append(link)

    for link in links:
        try:
            baixar_link(link)
        except Exception as e:
            print(f"❌ Erro no link {link}: {e}")

    print("\n🎉 Tudo finalizado.")

if __name__ == "__main__":
    main()