from pathlib import Path
import subprocess
import sys

IMAGES_DIR = Path("images")
BRANCH = "main"
REMOTE = "origin"


def run(cmd, *, check=False):
    print("\n> " + " ".join(cmd))
    result = subprocess.run(cmd, text=True)
    if check and result.returncode != 0:
        print("\nERRO: comando falhou. Parando.")
        sys.exit(result.returncode)
    return result.returncode == 0


def output(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def has_staged_changes_for(path: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", path.as_posix()],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def discover_folders():
    if not IMAGES_DIR.exists():
        print("ERRO: pasta images não encontrada.")
        sys.exit(1)

    folders = []

    for ano in sorted(IMAGES_DIR.iterdir()):
        if not ano.is_dir():
            continue
        for edicao in sorted(ano.iterdir()):
            if not edicao.is_dir():
                continue
            for marca in sorted(edicao.iterdir()):
                if marca.is_dir():
                    folders.append(marca)

    return folders


def main():
    print("Subindo imagens pasta por pasta...")
    print("Este script ignora pastas sem mudanças novas.")

    run(["git", "config", "gc.auto", "0"])

    # Evita começar com repositório sujo sem querer misturar coisas.
    status = output(["git", "status", "--porcelain"])
    if status:
        print("\nATENÇÃO: existem mudanças pendentes no projeto.")
        print("Vou continuar, mas cada commit será feito só com a pasta de imagem atual.")

    folders = discover_folders()
    print(f"\n{len(folders)} pastas de desfile encontradas.")

    for folder in folders:
        nome = folder.as_posix().replace("images/", "")

        print("\n" + "=" * 72)
        print(f"Pasta: {nome}")
        print("=" * 72)

        # Limpa staging antes de cada pasta.
        run(["git", "reset", "--quiet"])

        # -f é essencial caso images esteja no .gitignore.
        add_ok = run(["git", "add", "-f", "--", folder.as_posix()])
        if not add_ok:
            print("Erro no git add desta pasta. Pulando para a próxima.")
            continue

        if not has_staged_changes_for(folder):
            print("Nada novo nesta pasta. Pulando.")
            continue

        commit_msg = f"Adicionar imagens {nome}"
        commit_ok = run(["git", "commit", "-m", commit_msg])

        if not commit_ok:
            print("Commit falhou. Limpando staging e pulando.")
            run(["git", "reset", "--quiet"])
            continue

        push_ok = run(["git", "push", REMOTE, BRANCH])

        if not push_ok:
            print("\nPush falhou. Provavelmente o remoto tem coisa nova.")
            print("Rode estes comandos e depois execute o script de novo:")
            print(f"git pull --rebase {REMOTE} {BRANCH}")
            print(f"git push {REMOTE} {BRANCH}")
            sys.exit(1)

    run(["git", "reset", "--quiet"])
    print("\nFinalizado. Todas as pastas novas foram processadas.")


if __name__ == "__main__":
    main()
