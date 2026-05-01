import re
import time
import requests
from pathlib import Path
from urllib.parse import unquote

DATA_JS = Path("data.js")
PASTA_DESTINO = Path("images")
ARQUIVO_ERROS = Path("erros_download.txt")

erros = []

def limpar_url(url):
    """
    Remove transformações do Cloudinary, tipo:
    /f_auto,q_auto,w_1200/
    e volta para a URL original.
    """
    if "/upload/" not in url:
        return url

    base, resto = url.split("/upload/", 1)

    if "arquivo-desfiles/" in resto:
        caminho = resto.split("arquivo-desfiles/", 1)[1]
        return f"{base}/upload/arquivo-desfiles/{caminho}"

    return url


def caminho_destino_por_url(url):
    """
    Cria o caminho local dentro de images/
    baseado no trecho depois de arquivo-desfiles/
    """
    if "arquivo-desfiles/" not in url:
        return None

    caminho = url.split("arquivo-desfiles/", 1)[1]
    caminho = unquote(caminho)

    return PASTA_DESTINO / caminho


def baixar_arquivo(url, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and destino.stat().st_size > 0:
        return "existe"

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    destino.write_bytes(response.content)
    return "baixado"


def main():
    if not DATA_JS.exists():
        print("ERRO: data.js não encontrado na pasta atual.")
        return

    texto = DATA_JS.read_text(encoding="utf-8")

    urls = re.findall(r'https://res\.cloudinary\.com/[^"\']+', texto)

    urls = [limpar_url(url) for url in urls]

    # remove URLs duplicadas mantendo a ordem
    urls_unicas = []
    vistas = set()

    for url in urls:
        if url not in vistas:
            vistas.add(url)
            urls_unicas.append(url)

    total = len(urls_unicas)

    print(f"Encontradas {total} URLs únicas do Cloudinary.\n")

    for i, url in enumerate(urls_unicas, start=1):
        destino = caminho_destino_por_url(url)

        if destino is None:
            continue

        try:
            status = baixar_arquivo(url, destino)

            if status == "existe":
                print(f"[{i}/{total}] Já existe: {destino}")
            else:
                print(f"[{i}/{total}] Baixado: {destino}")

        except Exception as erro:
            print(f"[{i}/{total}] ERRO: {url}")
            print(erro)

            erros.append({
                "url": url,
                "destino": str(destino),
                "erro": str(erro)
            })

        # pausa pequena para não martelar o servidor
        time.sleep(0.05)

    if erros:
        with ARQUIVO_ERROS.open("w", encoding="utf-8") as f:
            for item in erros:
                f.write("URL: " + item["url"] + "\n")
                f.write("DESTINO: " + item["destino"] + "\n")
                f.write("ERRO: " + item["erro"] + "\n")
                f.write("-" * 80 + "\n")

        print(f"\n{len(erros)} erro(s) salvo(s) em {ARQUIVO_ERROS}")

    print("\nDownload finalizado.")


if __name__ == "__main__":
    main()