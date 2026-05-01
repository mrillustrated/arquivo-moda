from pathlib import Path
import subprocess

IMAGES_DIR = Path("images")

def run(cmd):
    print("\n> " + " ".join(cmd))
    return subprocess.run(cmd).returncode == 0

def has_staged_changes_for(path):
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", str(path)],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())

def main():
    run(["git", "config", "gc.auto", "0"])

    desfiles = []

    for ano in sorted(IMAGES_DIR.iterdir()):
        if not ano.is_dir():
            continue

        for edicao in sorted(ano.iterdir()):
            if not edicao.is_dir():
                continue

            for marca in sorted(edicao.iterdir()):
                if marca.is_dir():
                    desfiles.append(marca)

    print(f"{len(desfiles)} desfiles encontrados.")

    for desfile in desfiles:
        nome = desfile.as_posix().replace("images/", "")

        print("\n" + "=" * 70)
        print(f"Subindo: {nome}")
        print("=" * 70)

        run(["git", "reset"])

        if not run(["git", "add", "-A", "--", str(desfile)]):
            print("Erro no git add. Parando.")
            break

        if not has_staged_changes_for(desfile):
            print("Nada novo nesse desfile. Pulando.")
            continue

        commit_ok = run(["git", "-c", "gc.auto=0", "commit", "-m", f"Adicionar imagens {nome}"])

        if not commit_ok:
            print("Commit deu erro. Tentando push mesmo assim...")

        if not run(["git", "push"]):
            print("Erro no push. Rode o script de novo depois.")
            break

    print("\nFinalizado.")

if __name__ == "__main__":
    main()