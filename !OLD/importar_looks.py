from __future__ import annotations

import json
import os
import shutil
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from PIL import Image, ImageTk

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CLOUDINARY_ROOT_FOLDER = "arquivo-desfiles"

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def slugify_folder_name(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def normalize_edition_folder(edicao: str) -> str:
    return slugify_folder_name(edicao)


def collect_images(source_dir: Path) -> list[Path]:
    return sorted(
        [
            p for p in source_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
        ],
        key=lambda p: p.name.lower()
    )


def detect_next_id(data_js_path: Path) -> int:
    if not data_js_path.exists():
        return 1

    text = data_js_path.read_text(encoding="utf-8")
    ids = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("id:") or stripped.startswith('"id":'):
            try:
                value = stripped.split(":", 1)[1].strip().rstrip(",")
                ids.append(int(value))
            except ValueError:
                pass

    return max(ids) + 1 if ids else 1


def optimize_cloudinary_url(url: str, width: int) -> str:
    if "/image/upload/" not in url:
        return url

    if "/image/upload/f_auto,q_auto" in url:
        return url

    return url.replace(
        "/image/upload/",
        f"/image/upload/f_auto,q_auto,w_{width}/"
    )


def make_data_block(
    *,
    item_id: int,
    image_path: str,
    thumb_path: str,
    marca: str,
    modelo: str,
    ano: int,
    edicao: str,
    desfile: str,
    tags: list[str],
) -> str:
    tags_str = ", ".join(json.dumps(tag, ensure_ascii=False) for tag in tags)

    return f"""  {{
    id: {item_id},
    image: "{image_path}",
    thumb: "{thumb_path}",
    marca: {json.dumps(marca, ensure_ascii=False)},
    modelo: {json.dumps(modelo, ensure_ascii=False)},
    ano: {ano},
    edicao: {json.dumps(edicao, ensure_ascii=False)},
    desfile: {json.dumps(desfile, ensure_ascii=False)},
    tags: [{tags_str}]
  }}"""


def append_to_data_js(data_js_path: Path, blocks: list[str]) -> None:
    if not data_js_path.exists():
        data_js_path.write_text("const data = [\n];\n", encoding="utf-8")

    content = data_js_path.read_text(encoding="utf-8").strip()

    if not content.startswith("const data = [") or not content.endswith("];"):
        raise ValueError("O data.js precisa estar no formato: const data = [ ... ];")

    inner = content[len("const data = ["): -2].strip()
    addition = ",\n".join(blocks)

    if inner:
        new_inner = inner.rstrip()
        if not new_inner.endswith(","):
            new_inner += ","
        new_inner += "\n" + addition
    else:
        new_inner = addition

    data_js_path.write_text(
        "const data = [\n" + new_inner + "\n];\n",
        encoding="utf-8"
    )


def upload_to_cloudinary(local_file: Path, public_id: str) -> str:
    result = cloudinary.uploader.upload(
        str(local_file),
        public_id=public_id,
        overwrite=True,
        resource_type="image",
    )

    return result["secure_url"]


@dataclass
class ImageItemUI:
    path: Path
    preview: ImageTk.PhotoImage
    modelo_var: tk.StringVar
    tags_var: tk.StringVar


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        canvas = tk.Canvas(self, bg="#111111", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)

        self.scrollable_frame = ttk.Frame(canvas)
        self.window_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self.window_id, width=e.width)
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Importador de Looks + Cloudinary")
        self.root.geometry("980x820")
        self.root.configure(bg="#111111")

        self.source_var = tk.StringVar()
        self.project_var = tk.StringVar()
        self.ano_var = tk.StringVar()
        self.edicao_var = tk.StringVar()
        self.marca_var = tk.StringVar()
        self.desfile_var = tk.StringVar()
        self.tags_padrao_var = tk.StringVar()

        self.move_var = tk.BooleanVar(value=False)
        self.copy_local_var = tk.BooleanVar(value=True)
        self.cloudinary_var = tk.BooleanVar(value=True)

        self.items_ui: list[ImageItemUI] = []

        self._build_ui()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#111111", foreground="white", font=("Arial", 11))
        style.configure("TButton", font=("Arial", 10))
        style.configure("TCheckbutton", background="#111111", foreground="white")

        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Importador de Looks + Cloudinary",
            bg="#111111",
            fg="white",
            font=("Arial", 20, "bold")
        ).pack(anchor="w", pady=(0, 16))

        self._field_with_button(container, "Pasta com imagens", self.source_var, self.select_source)
        self._field_with_button(container, "Pasta do projeto", self.project_var, self.select_project)

        top_grid = ttk.Frame(container)
        top_grid.pack(fill="x", pady=(8, 0))

        self._small_field(top_grid, "Ano", self.ano_var, 0, 0)
        self._small_field(top_grid, "Edição", self.edicao_var, 0, 1)
        self._small_field(top_grid, "Marca", self.marca_var, 0, 2)

        self._field(container, "Desfile", self.desfile_var, placeholder="Ex: AZ Marias RIOFW01")
        self._field(container, "Tags padrão (opcional)", self.tags_padrao_var, placeholder="Ex: couro, preto, minimalista")

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(10, 10))

        ttk.Checkbutton(
            controls,
            text="Subir para Cloudinary",
            variable=self.cloudinary_var
        ).pack(side="left")

        ttk.Checkbutton(
            controls,
            text="Copiar também para pasta local",
            variable=self.copy_local_var
        ).pack(side="left", padx=(18, 0))

        ttk.Checkbutton(
            controls,
            text="Mover arquivos em vez de copiar",
            variable=self.move_var
        ).pack(side="left", padx=(18, 0))

        ttk.Button(controls, text="Carregar imagens", command=self.load_images).pack(side="right")
        ttk.Button(controls, text="Importar", command=self.import_files).pack(side="right", padx=(0, 10))

        self.progress = ttk.Progressbar(container, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 12))

        tk.Label(
            container,
            text="Prévia e campos por imagem",
            bg="#111111",
            fg="white",
            font=("Arial", 11)
        ).pack(anchor="w", pady=(4, 8))

        self.preview_frame = ScrollableFrame(container)
        self.preview_frame.pack(fill="both", expand=True)

        tk.Label(
            container,
            text="Resumo",
            bg="#111111",
            fg="white",
            font=("Arial", 11)
        ).pack(anchor="w", pady=(12, 6))

        self.log_text = tk.Text(
            container,
            height=8,
            bg="#0b0b0b",
            fg="#d9d9d9",
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="x")

    def _field(self, parent, label_text: str, var: tk.StringVar, placeholder: str = "") -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=6)

        ttk.Label(frame, text=label_text).pack(anchor="w")

        entry = tk.Entry(
            frame,
            textvariable=var,
            bg="#222222",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Arial", 10)
        )
        entry.pack(fill="x", pady=(4, 0), ipady=8)

        if placeholder:
            entry.insert(0, placeholder)
            entry.config(fg="#999999")

            def on_focus_in(event):
                if entry.get() == placeholder:
                    entry.delete(0, tk.END)
                    entry.config(fg="white")

            def on_focus_out(event):
                if not entry.get():
                    entry.insert(0, placeholder)
                    entry.config(fg="#999999")

            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

    def _small_field(self, parent, label_text: str, var: tk.StringVar, row: int, col: int) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, sticky="ew", padx=(0, 10), pady=4)
        parent.columnconfigure(col, weight=1)

        ttk.Label(frame, text=label_text).pack(anchor="w")

        tk.Entry(
            frame,
            textvariable=var,
            bg="#222222",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Arial", 10)
        ).pack(fill="x", pady=(4, 0), ipady=8)

    def _field_with_button(self, parent, label_text: str, var: tk.StringVar, button_command) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=6)

        ttk.Label(frame, text=label_text).pack(anchor="w")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(4, 0))

        tk.Entry(
            row,
            textvariable=var,
            bg="#222222",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Arial", 10)
        ).pack(side="left", fill="x", expand=True, ipady=8)

        ttk.Button(row, text="Selecionar", command=button_command).pack(side="left", padx=(10, 0))

    def select_source(self) -> None:
        path = filedialog.askdirectory(title="Escolha a pasta com as imagens")
        if path:
            self.source_var.set(path)

    def select_project(self) -> None:
        path = filedialog.askdirectory(title="Escolha a pasta do projeto")
        if path:
            self.project_var.set(path)

    def _clean_placeholder_value(self, raw: str, placeholder: str) -> str:
        raw = raw.strip()
        return "" if raw == placeholder else raw

    def load_images(self) -> None:
        try:
            source_dir = Path(self.source_var.get()).expanduser().resolve()

            if not source_dir.exists() or not source_dir.is_dir():
                raise ValueError("Selecione uma pasta de imagens válida.")

            files = collect_images(source_dir)

            if not files:
                raise ValueError("Nenhuma imagem suportada encontrada na pasta escolhida.")

            self._clear_preview()

            default_tags = self._clean_placeholder_value(
                self.tags_padrao_var.get(),
                "Ex: couro, preto, minimalista"
            )

            for index, path in enumerate(files, start=1):
                self._add_image_row(path, index, default_tags)

            self.progress["value"] = 0
            self.progress["maximum"] = len(files)

            self._write_log(f"{len(files)} imagem(ns) carregada(s).")

        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _clear_preview(self) -> None:
        for child in self.preview_frame.scrollable_frame.winfo_children():
            child.destroy()
        self.items_ui.clear()

    def _add_image_row(self, path: Path, index: int, default_tags: str) -> None:
        frame = tk.Frame(self.preview_frame.scrollable_frame, bg="#171717", padx=10, pady=10)
        frame.pack(fill="x", pady=(0, 10))

        try:
            image = Image.open(path)
            image.thumbnail((120, 160))
            preview = ImageTk.PhotoImage(image)
        except Exception:
            image = Image.new("RGB", (120, 160), color="#333333")
            preview = ImageTk.PhotoImage(image)

        thumb_label = tk.Label(frame, image=preview, bg="#171717")
        thumb_label.image = preview
        thumb_label.grid(row=0, column=0, rowspan=3, sticky="nw")

        tk.Label(
            frame,
            text=f"{index:02d} — {path.name}",
            bg="#171717",
            fg="white",
            font=("Arial", 10, "bold"),
            anchor="w"
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 8))

        modelo_var = tk.StringVar()
        tags_var = tk.StringVar(value=default_tags)

        tk.Label(frame, text="Modelo", bg="#171717", fg="white", anchor="w").grid(
            row=1, column=1, sticky="w", padx=(12, 0)
        )

        tk.Entry(
            frame,
            textvariable=modelo_var,
            bg="#222222",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Arial", 10)
        ).grid(row=1, column=2, sticky="ew", padx=(10, 0), ipady=6)

        tk.Label(frame, text="Tags", bg="#171717", fg="white", anchor="w").grid(
            row=2, column=1, sticky="w", padx=(12, 0), pady=(8, 0)
        )

        tk.Entry(
            frame,
            textvariable=tags_var,
            bg="#222222",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Arial", 10)
        ).grid(row=2, column=2, sticky="ew", padx=(10, 0), pady=(8, 0), ipady=6)

        frame.grid_columnconfigure(2, weight=1)

        self.items_ui.append(
            ImageItemUI(
                path=path,
                preview=preview,
                modelo_var=modelo_var,
                tags_var=tags_var,
            )
        )

    def import_files(self) -> None:
        try:
            source_dir = Path(self.source_var.get()).expanduser().resolve()
            project_dir = Path(self.project_var.get()).expanduser().resolve()

            if not source_dir.exists() or not source_dir.is_dir():
                raise ValueError("Selecione uma pasta de imagens válida.")

            if not project_dir.exists() or not project_dir.is_dir():
                raise ValueError("Selecione a pasta do projeto.")

            if self.cloudinary_var.get():
                if (
                    not os.getenv("CLOUDINARY_CLOUD_NAME")
                    or not os.getenv("CLOUDINARY_API_KEY")
                    or not os.getenv("CLOUDINARY_API_SECRET")
                ):
                    raise ValueError("Cloudinary não configurado. Confira o arquivo .env.")

            ano_raw = self.ano_var.get().strip()

            if not ano_raw.isdigit():
                raise ValueError("Ano precisa ser um número, ex: 2026.")

            ano = int(ano_raw)
            edicao = self.edicao_var.get().strip()
            marca = self.marca_var.get().strip()
            desfile = self._clean_placeholder_value(self.desfile_var.get(), "Ex: AZ Marias RIOFW01")

            if not edicao:
                raise ValueError("Preencha a edição.")

            if not marca:
                raise ValueError("Preencha a marca.")

            if not desfile:
                desfile = f"{marca} {edicao}"

            if not self.items_ui:
                raise ValueError("Clique em 'Carregar imagens' antes de importar.")

            edicao_folder = normalize_edition_folder(edicao)
            marca_folder = slugify_folder_name(marca)

            dest_dir = project_dir / "images" / str(ano) / edicao_folder / marca_folder
            data_js_path = project_dir / "data.js"

            if self.copy_local_var.get():
                dest_dir.mkdir(parents=True, exist_ok=True)

            next_id = detect_next_id(data_js_path)
            blocks: list[str] = []
            logs: list[str] = []

            self.progress["value"] = 0
            self.progress["maximum"] = len(self.items_ui)
            self.root.update_idletasks()

            for index, item in enumerate(self.items_ui, start=1):
                extension = item.path.suffix.lower()
                new_name = f"look{index:02d}{extension}"

                local_relative_path = (
                    Path("images") / str(ano) / edicao_folder / marca_folder / new_name
                ).as_posix()

                local_file_for_upload = item.path

                if self.copy_local_var.get():
                    dest_file = dest_dir / new_name

                    if self.move_var.get():
                        shutil.move(str(item.path), str(dest_file))
                    else:
                        shutil.copy2(item.path, dest_file)

                    local_file_for_upload = dest_file

                image_path_for_data = local_relative_path
                thumb_path_for_data = local_relative_path

                if self.cloudinary_var.get():
                    public_id = (
                        f"{CLOUDINARY_ROOT_FOLDER}/"
                        f"{ano}/"
                        f"{edicao_folder}/"
                        f"{marca_folder}/"
                        f"look{index:02d}"
                    )

                    cloudinary_url = upload_to_cloudinary(local_file_for_upload, public_id)

                    image_path_for_data = optimize_cloudinary_url(cloudinary_url, 1200)
                    thumb_path_for_data = optimize_cloudinary_url(cloudinary_url, 420)

                modelo = item.modelo_var.get().strip()
                tags = [tag.strip() for tag in item.tags_var.get().split(",") if tag.strip()]

                ano_tag = str(ano)
                if ano_tag not in tags:
                    tags.append(ano_tag)

                block = make_data_block(
                    item_id=next_id,
                    image_path=image_path_for_data,
                    thumb_path=thumb_path_for_data,
                    marca=marca,
                    modelo=modelo,
                    ano=ano,
                    edicao=edicao,
                    desfile=desfile,
                    tags=tags,
                )

                blocks.append(block)

                logs.append(
                    f"{item.path.name} -> {image_path_for_data}"
                )

                next_id += 1

                self.progress["value"] = index
                self.root.update_idletasks()

            append_to_data_js(data_js_path, blocks)

            summary = [
                "Importação concluída.",
                "",
                f"Data.js atualizado: {data_js_path}",
                "",
                "Arquivos:"
            ] + logs

            self._write_log("\n".join(summary))
            messagebox.showinfo("Concluído", "Importação concluída com sucesso.")

        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def _write_log(self, text: str) -> None:
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, text)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()