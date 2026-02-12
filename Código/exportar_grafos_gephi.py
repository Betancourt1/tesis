"""Convierte los grafos guardados en ``grafos`` a archivos GEXF para Gephi."""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Iterable, Set

import networkx as nx


def find_graph_files(root: Path, extensions: Set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.suffix.lower() in extensions and path.is_file():
            yield path


def load_graph(path: Path):
    with path.open("rb") as f:
        return pickle.load(f)


def export_to_gexf(graph, source_path: Path, src_root: Path, out_root: Path) -> Path:
    relative = source_path.relative_to(src_root)
    out_path = (out_root / relative).with_suffix(".gexf")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_gexf(graph, out_path, encoding="utf-8")
    return out_path


def main() -> None:
    # El archivo vive en ``Código``; el directorio de grafos está un nivel arriba.
    repo_root = Path(__file__).resolve().parent.parent
    src_root = repo_root / "grafos"
    out_root = repo_root / "grafos"

    if not src_root.exists():
        raise SystemExit(f"No se encontró el directorio de entrada: {src_root}")

    exts = {".gpickle", ".pickle", ".pkl"}
    graph_files = list(find_graph_files(src_root, exts))
    if not graph_files:
        raise SystemExit(f"No se encontraron archivos con extensión {exts} en {src_root}")

    print(f"Exportando {len(graph_files)} grafos desde {src_root} a {out_root}...")
    for graph_path in graph_files:
        graph = load_graph(graph_path)
        out_path = export_to_gexf(graph, graph_path, src_root, out_root)
        print(f"- {graph_path.relative_to(src_root)} -> {out_path.relative_to(out_root)}")

    print("Listo. Abre los .gexf en Gephi.")


if __name__ == "__main__":
    main()
