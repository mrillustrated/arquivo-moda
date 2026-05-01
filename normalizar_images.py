from pathlib import Path
import unicodedata

ROOT = Path("images")

def slug(value):
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower()
    value = "".join(ch if ch.isalnum() or ch in ".-_" else "" for ch in value)
    return value

for path in sorted(ROOT.rglob("*"), key=lambda p: len(p.parts), reverse=True):
    novo_nome = slug(path.name)
    if novo_nome and novo_nome != path.name:
        novo_path = path.with_name(novo_nome)
        if not novo_path.exists():
            path.rename(novo_path)
            print(f"{path} -> {novo_path}")

print("Normalização concluída.")