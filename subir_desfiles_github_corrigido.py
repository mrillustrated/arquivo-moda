from pathlib import Path
import subprocess
import sys

IMAGES_DIR = Path("images")
BRANCH = "main"
REMOTE = "origin"


def run(cmd, *, stop_on_error=False):
    print("\n> " + " ".join(cmd))
    result = subprocess.run(cmd, text=True)

    if stop_on_error and result.returncode != 0:
        print("\nERRO: comando falhou. Parando para evitar bagunça no Git.")
        sys.exit(result.returncode)

    return result.returncode == 0


def get_output(cmd):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def has_staged_changes_for(path: Path) -> bool:
    output = get_output(["git", "diff", "--cached", "--name-only", "--", str(path)])
    return bool(output)


def has_local_changes() -> bool:
    output = get_output(["git", "status", "--porcelain"])
    return bool(output)


def find_desfiles():
    desfiles = []

    if not IMAGES_DIR.exists():
        print("ERRO: pasta 'images' não encontrada.")
        print("Coloque este script na pasta raiz do projeto, junto de data.js e da pasta images.")
        sys.exit(1)

    for ano in sorted(IMAGES_DIR.iterdir()):
        if not ano.is_dir():
            continue

        for edicao in sorted(ano.iterdir()):
            if not edicao.is_dir():
                continue

            for marca in sorted(edicao.iterdir()):
                if marca.is_dir():
                    desfiles.append(marca)

    return desfiles


def main():
    print("Iniciando upload das imagens pasta por pasta...\n")

    run(["git", "config", "gc.auto", "0"])

    desfiles = find_desfiles()
    print(f"{len(desfiles)} pastas de desfile encontradas.")

    if not desfiles:
        print("Nenhuma pasta de desfile encontrada em images/ano/edicao/marca.")
        return

    # Garante que estamos atualizados antes de começar.
    # Se falhar por conflito, o usuário resolve manualmente.
    print("\nAtualizando repositório antes de começar...")
    run(["git", "pull", "--rebase", REMOTE, BRANCH])

    for desfile in desfiles:
        nome = desfile.as_posix().replace("images/", "")

        print("\n" + "=" * 70)
        print(f"Processando: {nome}")
        print("=" * 70)

        # Limpa staged area antes de cada pasta, sem apagar arquivos locais.
        run(["git", "reset"])

        # O -f é essencial porque images/ pode estar no .gitignore.
        add_ok = run(["git", "add", "-f", "-A", "--", str(desfile)])

        if not add_ok:
            print("Erro no git add desta pasta. Pulando para a próxima.")
            continue

        if not has_staged_changes_for(desfile):
            print("Nada novo para commitar nessa pasta. Pulando.")
            continue

        commit_msg = f"Adicionar imagens {nome}"
        commit_ok = run(["git", "-c", "gc.auto=0", "commit", "-m", commit_msg])

        if not commit_ok:
            print("Commit falhou nessa pasta. Pulando para evitar bagunça.")
            continue

        push_ok = run(["git", "push", REMOTE, BRANCH])

        if not push_ok:
            print("\nPush falhou. Tentando atualizar com rebase e enviar de novo...")
            pull_ok = run(["git", "pull", "--rebase", REMOTE, BRANCH])

            if pull_ok:
                push_ok = run(["git", "push", REMOTE, BRANCH])

        if not push_ok:
            print("\nERRO: não consegui fazer push desta pasta.")
            print("Pare aqui, copie o erro do terminal e me mande.")
            break

    print("\n" + "=" * 70)
    print("Finalizado.")
    print("Se alguma pasta foi pulada como 'Nada novo', ela já estava igual no Git ou não tinha arquivo rastreável.")
    print("=" * 70)


if __name__ == "__main__":
    main()
