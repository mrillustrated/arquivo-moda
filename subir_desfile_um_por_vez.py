from pathlib import Path
import subprocess
import sys
import time

IMAGES_DIR = Path("images")
BRANCH = "main"
REMOTE = "origin"

# Se quiser limitar a uma edição específica, preencha aqui:
# EXEMPLO: SOMENTE_EDICAO = "riofw01"
SOMENTE_EDICAO = ""

# Se quiser começar a partir de uma marca específica, preencha aqui:
# EXEMPLO: COMEÇAR_EM = "aluf"
COMECAR_EM = ""

def run(cmd, stop_on_error=False):
    print("\n> " + " ".join(cmd), flush=True)
    result = subprocess.run(cmd, text=True)
    if stop_on_error and result.returncode != 0:
        print("\nERRO: comando falhou. Parando aqui.", flush=True)
        sys.exit(result.returncode)
    return result.returncode == 0

def capture(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def ensure_repo():
    if not Path(".git").exists():
        print("ERRO: rode este script dentro da pasta do repositório Git.", flush=True)
        sys.exit(1)

    if not IMAGES_DIR.exists():
        print("ERRO: pasta images/ não encontrada.", flush=True)
        sys.exit(1)

def staged_files():
    out, _, _ = capture(["git", "diff", "--cached", "--name-only"])
    return [line for line in out.splitlines() if line.strip()]

def working_tree_has_path(path):
    out, _, _ = capture(["git", "status", "--porcelain", "--", str(path)])
    return bool(out.strip())

def list_desfiles():
    desfiles = []

    for ano in sorted(IMAGES_DIR.iterdir()):
        if not ano.is_dir():
            continue

        for edicao in sorted(ano.iterdir()):
            if not edicao.is_dir():
                continue

            if SOMENTE_EDICAO and edicao.name.lower() != SOMENTE_EDICAO.lower():
                continue

            for marca in sorted(edicao.iterdir()):
                if marca.is_dir():
                    desfiles.append(marca)

    if COMECAR_EM:
        start = COMECAR_EM.lower()
        desfiles = [d for d in desfiles if d.name.lower() >= start]

    return desfiles

def commit_message_for(path):
    # images/2026/riofw01/aluf -> Adicionar imagens 2026/riofw01/aluf
    nome = path.as_posix().replace("images/", "", 1)
    return f"Adicionar imagens {nome}"

def main():
    ensure_repo()

    print("Configurando Git para não fazer auto-gc durante o processo...", flush=True)
    run(["git", "config", "gc.auto", "0"])

    # Importante: desfaz staged antigo para o script controlar uma pasta por vez.
    run(["git", "reset"])

    desfiles = list_desfiles()
    print(f"\n{len(desfiles)} pastas de desfile encontradas.", flush=True)

    for index, desfile in enumerate(desfiles, start=1):
        nome = desfile.as_posix().replace("images/", "", 1)

        print("\n" + "=" * 80, flush=True)
        print(f"[{index}/{len(desfiles)}] DESFILE: {nome}", flush=True)
        print("=" * 80, flush=True)

        # Limpa staging antes de cada desfile para evitar pacote acumulado.
        run(["git", "reset"])

        if not working_tree_has_path(desfile):
            print("Nada novo/modificado nessa pasta. Pulando.", flush=True)
            continue

        # -f força adicionar mesmo se images estiver no .gitignore.
        ok_add = run(["git", "add", "-f", "-A", "--", str(desfile)])
        if not ok_add:
            print("Erro no git add. Parando para você ver o erro acima.", flush=True)
            sys.exit(1)

        files = staged_files()
        files_this = [f for f in files if f.startswith(desfile.as_posix() + "/") or f == desfile.as_posix()]

        if not files_this:
            print("Nada foi staged para essa pasta. Pulando.", flush=True)
            continue

        print(f"{len(files_this)} arquivo(s) staged para este desfile.", flush=True)

        msg = commit_message_for(desfile)
        ok_commit = run(["git", "commit", "-m", msg])

        if not ok_commit:
            print("Commit falhou. Pode não haver alterações reais. Pulando.", flush=True)
            continue

        # Push imediatamente após cada commit.
        ok_push = run(["git", "push", REMOTE, BRANCH])

        if not ok_push:
            print("\nO push falhou neste desfile.", flush=True)
            print("Tentando pull --rebase e depois push de novo...", flush=True)

            ok_pull = run(["git", "pull", "--rebase", REMOTE, BRANCH])
            if not ok_pull:
                print("\nPull --rebase falhou. Resolva o conflito no Git e rode o script de novo.", flush=True)
                sys.exit(1)

            ok_push_2 = run(["git", "push", REMOTE, BRANCH])
            if not ok_push_2:
                print("\nPush falhou de novo. Parando para não acumular commits gigantes.", flush=True)
                print(f"Último desfile tentado: {nome}", flush=True)
                sys.exit(1)

        print(f"OK: {nome} enviado para o GitHub.", flush=True)

        # Pequena pausa para não martelar o GitHub.
        time.sleep(1)

    print("\nFinalizado. Conferindo status final:\n", flush=True)
    run(["git", "status"])

if __name__ == "__main__":
    main()
