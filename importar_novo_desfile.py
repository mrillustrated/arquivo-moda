from pathlib import Path
import json
import re
import shutil
import unicodedata

# ============================================================
# IMPORTADOR DE NOVOS DESFILES PARA O ARQUIVO DE MODA
# ============================================================
# O que ele faz:
# 1. Pede a pasta onde estão as imagens novas.
# 2. Pede ano, edição e marca.
# 3. Copia as imagens para: images/ANO/EDICAO/MARCA/look01.jpg...
# 4. Lê o data.js atual.
# 5. Adiciona apenas os looks novos no final do data.js.
# 6. Não mexe nos itens antigos.
#
# Depois você pode abrir o data.js no tag-editor.html para taguear.
# ============================================================

USUARIO_GITHUB = "mrillustrated"
REPO_GITHUB = "arquivo-moda"
BRANCH = "main"

DATA_JS = Path("data.js")
IMAGES_DIR = Path("images")

EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp"}

BASE_URL = f"https://cdn.jsdelivr.net/gh/{USUARIO_GITHUB}/{REPO_GITHUB}@{BRANCH}/images/"


def slugify(value: str) -> str:
    value = value.strip()
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def limpar_data_js(texto: str) -> str:
    texto = texto.strip()
    texto = re.sub(r"^\s*const\s+data\s*=\s*", "", texto)
    texto = re.sub(r";\s*$", "", texto)
    return texto


def carregar_data() -> list[dict]:
    if not DATA_JS.exists():
        print("data.js não encontrado. Vou criar um novo.")
        return []

    texto = DATA_JS.read_text(encoding="utf-8")
    texto_limpo = limpar_data_js(texto)

    try:
        data = json.loads(texto_limpo)
    except Exception as erro:
        print("ERRO: não consegui ler o data.js.")
        print("Confira se ele está no formato: const data = [...]")
        raise erro

    if not isinstance(data, list):
        raise ValueError("O data.js não contém um array.")

    return data


def salvar_data(data: list[dict]):
    conteudo = "const data = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    DATA_JS.write_text(conteudo, encoding="utf-8")


def listar_imagens(pasta_origem: Path) -> list[Path]:
    imagens = [
        p for p in pasta_origem.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSOES_VALIDAS
    ]

    def ordem(path: Path):
        nums = re.findall(r"\d+", path.stem)
        numero = int(nums[-1]) if nums else 999999
        return (numero, path.name.lower())

    return sorted(imagens, key=ordem)


def proximo_numero_look(pasta_destino: Path) -> int:
    existentes = []

    if pasta_destino.exists():
        for arquivo in pasta_destino.iterdir():
            if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_VALIDAS:
                nums = re.findall(r"\d+", arquivo.stem)
                if nums:
                    existentes.append(int(nums[-1]))

    return max(existentes, default=0) + 1


def url_para_relativa(url: str) -> str:
    value = str(url or "").strip().replace("\\", "/")

    if "/images/" in value:
        value = value.split("/images/", 1)[1]

    if value.startswith("images/"):
        value = value.replace("images/", "", 1)

    return value.lower()


def ja_existe_no_data(data: list[dict], caminho_relativo: str) -> bool:
    caminho_relativo = caminho_relativo.lower()
    for item in data:
        if url_para_relativa(item.get("image", "")) == caminho_relativo:
            return True
        if url_para_relativa(item.get("thumb", "")) == caminho_relativo:
            return True
    return False


def perguntar(texto: str, obrigatorio=True) -> str:
    while True:
        resposta = input(texto).strip()
        if resposta or not obrigatorio:
            return resposta
        print("Esse campo é obrigatório.")


def main():
    print("\n=== IMPORTAR NOVO DESFILE ===\n")

    pasta_origem_txt = perguntar("Cole o caminho da pasta com as imagens novas: ")
    pasta_origem = Path(pasta_origem_txt.strip('"').strip("'"))

    if not pasta_origem.exists() or not pasta_origem.is_dir():
        print("ERRO: pasta de origem não encontrada.")
        return

    imagens = listar_imagens(pasta_origem)

    if not imagens:
        print("ERRO: nenhuma imagem .jpg, .jpeg, .png ou .webp encontrada nessa pasta.")
        return

    print(f"\nEncontrei {len(imagens)} imagem(ns).\n")

    ano_txt = perguntar("Ano. Ex: 2026: ")
    if not ano_txt.isdigit():
        print("ERRO: ano precisa ser número.")
        return

    ano = int(ano_txt)

    edicao_input = perguntar("Edição. Ex: riofw01 ou spfwn55: ")
    marca_input = perguntar("Marca. Ex: Aluf: ")

    modelo_padrao = perguntar("Modelo padrão, opcional. Enter para deixar vazio: ", obrigatorio=False)
    tags_padrao_txt = perguntar("Tags padrão, opcional. Ex: preto, vestido. Enter para só usar o ano: ", obrigatorio=False)

    edicao_slug = slugify(edicao_input)
    marca_slug = slugify(marca_input)

    if not edicao_slug or not marca_slug:
        print("ERRO: edição ou marca inválida.")
        return

    pasta_destino = IMAGES_DIR / str(ano) / edicao_slug / marca_slug
    pasta_destino.mkdir(parents=True, exist_ok=True)

    data = carregar_data()

    tags_padrao = []
    if tags_padrao_txt:
        tags_padrao = [tag.strip() for tag in tags_padrao_txt.split(",") if tag.strip()]

    if str(ano) not in tags_padrao:
        tags_padrao.append(str(ano))

    inicio = proximo_numero_look(pasta_destino)

    novos_itens = []
    copiados = 0
    pulados = 0

    print("\nCopiando imagens e criando itens...\n")

    for offset, imagem_origem in enumerate(imagens):
        numero = inicio + offset
        extensao = imagem_origem.suffix.lower()
        nome_arquivo = f"look{numero:02d}{extensao}"

        destino = pasta_destino / nome_arquivo
        caminho_relativo = destino.relative_to(IMAGES_DIR).as_posix()
        url = BASE_URL + caminho_relativo

        if destino.exists():
            print(f"PULANDO: já existe no destino: {destino}")
            pulados += 1
            continue

        if ja_existe_no_data(data, caminho_relativo):
            print(f"PULANDO: já existe no data.js: {caminho_relativo}")
            pulados += 1
            continue

        shutil.copy2(imagem_origem, destino)
        copiados += 1

        item = {
            "image": url,
            "marca": marca_input.strip(),
            "ano": ano,
            "modelo": modelo_padrao.strip(),
            "edicao": edicao_slug,
            "desfile": f"{marca_input.strip()} {edicao_slug.upper()}",
            "tags": tags_padrao[:],
            "thumb": url
        }

        novos_itens.append(item)
        print(f"OK: {imagem_origem.name} -> {destino}")

    if novos_itens:
        data.extend(novos_itens)
        salvar_data(data)

    print("\n=== FINALIZADO ===")
    print(f"Imagens copiadas: {copiados}")
    print(f"Itens novos no data.js: {len(novos_itens)}")
    print(f"Pulados: {pulados}")
    print(f"Pasta destino: {pasta_destino}")

    print("\nPróximos comandos sugeridos:")
    print(f'git add -f "{pasta_destino.as_posix()}" data.js')
    print(f'git commit -m "Adicionar desfile {marca_input.strip()} {edicao_slug.upper()}"')
    print("git push origin main")
    print("\nDepois abra o data.js no tag-editor para revisar tags/modelos.")


if __name__ == "__main__":
    main()
