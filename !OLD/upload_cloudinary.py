import os
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

PASTA_IMAGENS = Path("images")
PASTA_CLOUDINARY = "arquivo-desfiles"

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}

def upload_imagens():
    arquivos = [
        arquivo for arquivo in PASTA_IMAGENS.rglob("*")
        if arquivo.suffix.lower() in EXTENSOES
    ]

    total = len(arquivos)

    if total == 0:
        print("Nenhuma imagem encontrada na pasta images.")
        return

    print(f"Encontradas {total} imagens.\n")

    for index, arquivo in enumerate(arquivos, start=1):
        caminho_relativo = arquivo.relative_to(PASTA_IMAGENS).as_posix()
        public_id = caminho_relativo.rsplit(".", 1)[0]

        print(f"[{index}/{total}] Enviando: {caminho_relativo}")

        try:
            resultado = cloudinary.uploader.upload(
                str(arquivo),
                folder=PASTA_CLOUDINARY,
                public_id=public_id,
                overwrite=True,
                resource_type="image"
            )

            print("OK:", resultado["secure_url"])

        except Exception as erro:
            print("ERRO:", caminho_relativo)
            print(erro)

    print("\nUpload finalizado.")

upload_imagens()