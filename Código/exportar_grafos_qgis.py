"""Convierte los grafos guardados en ``grafos`` a GeoPackage para visualizarlos en QGIS."""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple

import geopandas as gpd
import networkx as nx  # Necesario para deserializar los grafos pickled
from shapely.geometry import LineString, Point


def find_graph_files(root: Path, extensions: Set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.suffix.lower() in extensions and path.is_file():
            yield path


def load_graph(path: Path):
    with path.open("rb") as f:
        return pickle.load(f)


def get_coord_keys(data: dict) -> Optional[Tuple[str, str]]:
    """Devuelve un par (lon_key, lat_key) si los atributos parecen contener coordenadas."""
    candidates = [
        ("lon", "lat"),
        ("stop_lon", "stop_lat"),
        ("longitude", "latitude"),
        ("longitud", "latitud"),
        ("x", "y"),
    ]
    for lon_key, lat_key in candidates:
        if lon_key in data and lat_key in data:
            return lon_key, lat_key
    return None


def extract_coords(data: dict, keys: Tuple[str, str]) -> Optional[Tuple[float, float]]:
    lon, lat = data.get(keys[0]), data.get(keys[1])
    if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
        return lon, lat
    return None


def graph_to_geodataframes(G) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    sample_keys = get_coord_keys(next(iter(G.nodes(data=True)))[1]) if G.number_of_nodes() else None
    if not sample_keys:
        raise ValueError("No se encontraron campos de coordenadas en los nodos.")

    nodes_records = []
    for node_id, data in G.nodes(data=True):
        coords = extract_coords(data, sample_keys)
        if coords is None:
            continue
        record = {**data, "id": node_id, "geometry": Point(coords)}
        nodes_records.append(record)

    if not nodes_records:
        raise ValueError("No se pudieron extraer coordenadas válidas de los nodos.")

    nodes_gdf = gpd.GeoDataFrame(nodes_records, crs="EPSG:4326")

    # Solo creamos aristas cuando ambos extremos tienen geometría válida.
    edges_records = []
    node_geom = {row["id"]: row["geometry"] for _, row in nodes_gdf.iterrows()}
    for u, v, data in G.edges(data=True):
        if u not in node_geom or v not in node_geom:
            continue
        line = LineString([node_geom[u], node_geom[v]])
        record = {**data, "u": u, "v": v, "geometry": line}
        edges_records.append(record)

    edges_gdf = gpd.GeoDataFrame(edges_records, crs=nodes_gdf.crs)
    return nodes_gdf, edges_gdf


def export_graph_to_geopackage(graph_path: Path, src_root: Path, out_root: Path) -> Path:
    G = load_graph(graph_path)
    nodes_gdf, edges_gdf = graph_to_geodataframes(G)

    relative = graph_path.relative_to(src_root)
    out_path = (out_root / relative).with_suffix(".gpkg")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    nodes_gdf.to_file(out_path, layer="nodes", driver="GPKG")
    if not edges_gdf.empty:
        edges_gdf.to_file(out_path, layer="edges", driver="GPKG")
    return out_path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    src_root = repo_root / "grafos"
    out_root = repo_root / "grafos_qgis"

    if not src_root.exists():
        raise SystemExit(f"No se encontró el directorio de entrada: {src_root}")

    exts = {".gpickle", ".pickle", ".pkl"}
    graph_files = list(find_graph_files(src_root, exts))
    if not graph_files:
        raise SystemExit(f"No se encontraron archivos con extensión {exts} en {src_root}")

    print(f"Exportando {len(graph_files)} grafos desde {src_root} a {out_root} (GeoPackage)...")
    successes, failures = 0, 0
    for graph_path in graph_files:
        try:
            out_path = export_graph_to_geopackage(graph_path, src_root, out_root)
            print(f"- {graph_path.relative_to(src_root)} -> {out_path.relative_to(out_root)}")
            successes += 1
        except Exception as exc:  # noqa: BLE001
            print(f"! No se pudo exportar {graph_path.relative_to(src_root)}: {exc}")
            failures += 1

    print(f"Listo. Exportados: {successes}, fallidos: {failures}. Abre los .gpkg en QGIS.")


if __name__ == "__main__":
    main()
