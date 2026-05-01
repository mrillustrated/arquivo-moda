from pathlib import Path

arquivo = Path("data.js")

txt = arquivo.read_text(encoding="utf-8")
txt = txt.replace("Sou de Algodão", "Sou De Algodão")
arquivo.write_text(txt, encoding="utf-8")

print("Corrigido: Marca Corrigida")