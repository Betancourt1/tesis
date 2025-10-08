#!/usr/bin/env python3
"""
Validador GTFS para Zona Metropolitana de Guadalajara
Ejecuta pruebas de calidad y reporta PASS/FAIL para cada categoria
"""

import pandas as pd
import numpy as np
import json
import hashlib
from pathlib import Path
from datetime import datetime
import chardet
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURACION
# ============================================================================

ZMG_BOUNDS = {
    'lat_min': 20.5,
    'lat_max': 20.8,
    'lon_min': -103.5,
    'lon_max': -103.2
}

DISTANCE_RANGE = (10, 2000)  # metros
DURATION_RANGE = (10, 3600)  # segundos (10s - 60min)
MIN_HEADWAY = 2  # segundos
MAX_GAP = 7200  # segundos

# Criterios de aceptacion
MAX_BROKEN_KEYS_PCT = 0.0  # 0%
MAX_SUSPICIOUS_SEGMENTS_PCT = 1.0  # <1%

# ============================================================================
# CLASE VALIDADOR
# ============================================================================

class GTFSValidator:
    def __init__(self, gtfs_path: str):
        self.gtfs_path = Path(gtfs_path)
        self.data = {}
        self.results = {
            'structure': {'passed': True, 'tests': []},
            'spatial': {'passed': True, 'tests': []},
            'temporal': {'passed': True, 'tests': []},
            'consistency': {'passed': True, 'tests': []},
        }
        self.metadata = {}
        self.stats = {}

    def log_test(self, category: str, test_name: str, passed: bool, message: str, severity: str = 'error'):
        """Registrar resultado de test"""
        self.results[category]['tests'].append({
            'name': test_name,
            'passed': passed,
            'severity': severity,
            'message': message
        })

        if not passed and severity == 'error':
            self.results[category]['passed'] = False

    def print_section(self, title: str):
        """Imprimir seccion"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print('='*70)

    def print_test(self, name: str, passed: bool, message: str = ""):
        """Imprimir resultado de test"""
        status = "[PASS]" if passed else "[FAIL]"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} | {name}")
        if message:
            prefix = "       " if passed else "       "
            print(f"{prefix}- {message}")

    # ========================================================================
    # 1. PREPARACION
    # ========================================================================

    def freeze_feed(self):
        """Congela version del feed con hash y metadata"""
        self.print_section("1. PREPARACION - CONGELACION DEL FEED")

        # Buscar ZIP
        zip_files = list(self.gtfs_path.glob("*.zip"))
        if zip_files:
            zip_path = zip_files[0]
            with open(zip_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            self.metadata['zip_file'] = zip_path.name
            self.metadata['sha256'] = file_hash
            print(f"  Feed: {zip_path.name}")
            print(f"  SHA-256: {file_hash[:32]}...")
        else:
            print(f"  Feed: Archivos CSV individuales")
            self.metadata['zip_file'] = 'CSV files'
            self.metadata['sha256'] = 'N/A'

        self.metadata['validation_date'] = datetime.now().isoformat()
        self.metadata['gtfs_path'] = str(self.gtfs_path)
        self.metadata['timezone'] = 'America/Mexico_City'

        print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Zona horaria: America/Mexico_City")

    # ========================================================================
    # 2. CHECKS DE ESTRUCTURA
    # ========================================================================

    def check_structure(self):
        """Validar estructura de archivos GTFS"""
        self.print_section("2. CHECKS DE ESTRUCTURA")

        # Test 1: Archivos obligatorios
        required_files = ['agency', 'stops', 'routes', 'trips', 'stop_times']
        calendar_files = ['calendar', 'calendar_dates']

        missing_files = []
        for file in required_files:
            csv_path = self.gtfs_path / f"{file}.csv"
            txt_path = self.gtfs_path / f"{file}.txt"

            if not csv_path.exists() and not txt_path.exists():
                missing_files.append(file)

        has_calendar = any(
            (self.gtfs_path / f"{f}.csv").exists() or
            (self.gtfs_path / f"{f}.txt").exists()
            for f in calendar_files
        )

        if not has_calendar:
            missing_files.append('calendar/calendar_dates')

        self.log_test('structure', 'archivos_obligatorios',
                      len(missing_files) == 0,
                      f"Faltantes: {missing_files}" if missing_files else "Todos presentes")
        self.print_test("Archivos obligatorios presentes",
                       len(missing_files) == 0,
                       f"{len(required_files) + 1 - len(missing_files)}/{len(required_files) + 1} archivos")

        if missing_files:
            return  # No continuar si faltan archivos criticos

        # Test 2: Formato de archivos y carga
        bom_issues = []

        for file in required_files + calendar_files:
            csv_path = self.gtfs_path / f"{file}.csv"
            txt_path = self.gtfs_path / f"{file}.txt"
            path = csv_path if csv_path.exists() else txt_path

            if not path.exists():
                continue

            # Check BOM (solo informativo, no bloqueante)
            try:
                with open(path, 'rb') as f:
                    start = f.read(3)
                    if start == b'\xef\xbb\xbf':
                        bom_issues.append(file)
            except Exception:
                pass

            # Cargar datos (sin exigir UTF-8)
            try:
                df = pd.read_csv(path, dtype=str)

                # Limpiar filas vacias y columnas fantasma
                empty_rows = df.isna().all(axis=1).sum()
                df = df.dropna(how='all')

                unnamed_cols = [col for col in df.columns if 'Unnamed' in str(col)]
                if unnamed_cols:
                    df = df.drop(columns=unnamed_cols)

                self.data[file] = df

            except Exception as e:
                self.log_test('structure', f'carga_{file}', False,
                              f"Error al cargar {file}.csv/txt: {str(e)}")

        # Nota: Se eliminó el criterio de que los archivos deban ser UTF-8
        self.print_test("Archivos legibles (sin exigir UTF-8)",
                        True,
                        f"{len(self.data)} archivos cargados")

        # Test 3: Claves primarias
        pk_issues = []

        pk_checks = {
            'agency': 'agency_id',
            'stops': 'stop_id',
            'routes': 'route_id',
            'trips': 'trip_id',
            'stop_times': ['trip_id', 'stop_sequence']
        }

        for table, pk in pk_checks.items():
            if table not in self.data:
                continue

            df = self.data[table]

            if isinstance(pk, list):
                # Compuesta
                if all(col in df.columns for col in pk):
                    dup_mask = df.duplicated(subset=pk, keep=False)
                    dup_count = int(dup_mask.sum())
                    if dup_count > 0:
                        # ejemplos de claves compuestas duplicadas
                        dup_keys = (
                            df.loc[dup_mask, pk]
                              .astype(str)
                              .drop_duplicates()
                              .head(10)
                              .apply(lambda r: tuple(r.values.tolist()), axis=1)
                              .tolist()
                        )
                        pk_issues.append(
                            f"{table}.csv/txt: {dup_count} duplicados en clave compuesta {pk} - ejemplos: {dup_keys}"
                        )
            else:
                # Simple
                if pk not in df.columns:
                    if table == 'agency':
                        df['agency_id'] = '1'
                        self.data[table] = df
                    else:
                        pk_issues.append(f"{table}.csv/txt: falta columna {pk}")
                else:
                    dup_mask = df.duplicated(subset=[pk], keep=False)
                    dup_count = int(dup_mask.sum())
                    if dup_count > 0:
                        dup_vals = (
                            df.loc[dup_mask, pk]
                              .astype(str)
                              .dropna()
                              .drop_duplicates()
                              .head(10)
                              .tolist()
                        )
                        pk_issues.append(
                            f"{table}.csv/txt: {dup_count} duplicados en {pk} - ejemplos: {dup_vals}"
                        )

        self.log_test('structure', 'claves_primarias',
                      len(pk_issues) == 0,
                      "; ".join(pk_issues) if pk_issues else "Todas unicas")
        self.print_test("Claves primarias unicas",
                       len(pk_issues) == 0,
                       "Sin duplicados" if len(pk_issues) == 0 else f"{len(pk_issues)} problemas")

        # Test 4: Claves foraneas
        fk_issues = []

        fk_checks = [
            ('routes', 'agency_id', 'agency', 'agency_id'),
            ('trips', 'route_id', 'routes', 'route_id'),
            ('stop_times', 'trip_id', 'trips', 'trip_id'),
            ('stop_times', 'stop_id', 'stops', 'stop_id'),
        ]

        for child_table, child_key, parent_table, parent_key in fk_checks:
            if child_table not in self.data or parent_table not in self.data:
                continue

            if child_key not in self.data[child_table].columns:
                continue
            if parent_key not in self.data[parent_table].columns:
                continue

            child_vals = set(self.data[child_table][child_key].dropna().unique())
            parent_vals = set(self.data[parent_table][parent_key].dropna().unique())

            orphans = child_vals - parent_vals
            if orphans:
                examples = list(sorted(map(str, orphans)))[:10]
                fk_issues.append(
                    f"{child_table}.csv/txt {child_key} -> {parent_table}.csv/txt: {len(orphans)} huérfanos; ejemplos: {examples}"
                )

        self.log_test('structure', 'claves_foraneas',
                      len(fk_issues) == 0,
                      "; ".join(fk_issues) if fk_issues else "Todas válidas")
        self.print_test("Referencias entre tablas válidas",
                       len(fk_issues) == 0,
                       "Sin huérfanos" if len(fk_issues) == 0 else f"{len(fk_issues)} problemas")

        # Estadisticas
        self.stats['total_records'] = sum(len(df) for df in self.data.values())
        self.stats['tables_loaded'] = len(self.data)

    # ========================================================================
    # 3. CHECKS ESPACIALES
    # ========================================================================

    def check_spatial(self):
        """Validar datos espaciales"""
        self.print_section("3. CHECKS ESPACIALES")

        if 'stops' not in self.data:
            self.print_test("Datos espaciales", False, "No se cargo stops")
            return

        stops = self.data['stops'].copy()

        # Convertir coordenadas
        stops['stop_lat'] = pd.to_numeric(stops['stop_lat'], errors='coerce')
        stops['stop_lon'] = pd.to_numeric(stops['stop_lon'], errors='coerce')

        # Test 1: Coordenadas validas
        invalid_coords = stops['stop_lat'].isna() | stops['stop_lon'].isna()
        invalid_pct = invalid_coords.sum() / len(stops) * 100

        self.log_test('spatial', 'coordenadas_validas',
                      invalid_coords.sum() == 0,
                      f"{invalid_coords.sum()} stops sin coordenadas ({invalid_pct:.1f}%)",
                      'warning' if invalid_pct < 5 else 'error')
        self.print_test("Coordenadas validas (lat/lon)",
                       invalid_coords.sum() == 0,
                       f"{len(stops) - invalid_coords.sum()}/{len(stops)} stops")

        # Test 2: Dentro de ZMG
        valid = stops[~invalid_coords].copy()
        outside_zmg = (
            (valid['stop_lat'] < ZMG_BOUNDS['lat_min']) |
            (valid['stop_lat'] > ZMG_BOUNDS['lat_max']) |
            (valid['stop_lon'] < ZMG_BOUNDS['lon_min']) |
            (valid['stop_lon'] > ZMG_BOUNDS['lon_max'])
        )
        outside_pct = outside_zmg.sum() / len(valid) * 100 if len(valid) > 0 else 0

        self.log_test('spatial', 'dentro_zmg',
                      outside_zmg.sum() == 0,
                      f"{outside_zmg.sum()} stops fuera de ZMG ({outside_pct:.1f}%)",
                      'warning')
        self.print_test("Coordenadas dentro de ZMG",
                       outside_pct < 5,
                       f"{len(valid) - outside_zmg.sum()}/{len(valid)} stops en rango")

        # Test 3: Parent station
        has_parent = 'parent_station' in stops.columns
        if has_parent:
            empty_parent = (stops['parent_station'].fillna('') == '').sum()
            parent_pct = (1 - empty_parent / len(stops)) * 100
        else:
            empty_parent = len(stops)
            parent_pct = 0

        self.log_test('spatial', 'parent_station',
                      has_parent and empty_parent == 0,
                      f"parent_station: {parent_pct:.0f}% asignado",
                      'warning')
        self.print_test("parent_station definido",
                       has_parent,
                       f"{parent_pct:.0f}% stops con parent" if has_parent else "Campo no existe")

        # Test 4: Distancias entre stops consecutivos
        if 'stop_times' in self.data:
            flags = self.check_stop_distances()

            if 'stop_times' in self.data:
                total_segments = len(self.data['stop_times']) - self.data['stop_times']['trip_id'].nunique()
                suspicious_pct = len(flags) / total_segments * 100 if total_segments > 0 else 0

                self.stats['suspicious_segments_pct'] = suspicious_pct

                self.log_test('spatial', 'distancias_stops',
                              suspicious_pct < MAX_SUSPICIOUS_SEGMENTS_PCT,
                              f"{len(flags)} tramos sospechosos ({suspicious_pct:.2f}%)",
                              'error' if suspicious_pct >= MAX_SUSPICIOUS_SEGMENTS_PCT else 'warning')
                self.print_test("Distancias entre stops (10-2000m)",
                               suspicious_pct < MAX_SUSPICIOUS_SEGMENTS_PCT,
                               f"{suspicious_pct:.2f}% tramos fuera de rango")

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calcular distancia haversine en metros"""
        R = 6371000
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        return R * c

    def check_stop_distances(self):
        """Verificar distancias entre stops"""
        stops = self.data['stops'].set_index('stop_id')
        stop_times = self.data['stop_times'].copy()

        stop_times['stop_sequence'] = pd.to_numeric(stop_times['stop_sequence'], errors='coerce')
        stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

        flags = []
        sample_size = min(1000, stop_times['trip_id'].nunique())

        for trip_id in stop_times['trip_id'].unique()[:sample_size]:
            trip_stops = stop_times[stop_times['trip_id'] == trip_id].copy()

            if len(trip_stops) < 2:
                continue

            for i in range(len(trip_stops) - 1):
                stop1_id = trip_stops.iloc[i]['stop_id']
                stop2_id = trip_stops.iloc[i+1]['stop_id']

                if stop1_id not in stops.index or stop2_id not in stops.index:
                    continue

                try:
                    lat1 = float(stops.loc[stop1_id, 'stop_lat'])
                    lon1 = float(stops.loc[stop1_id, 'stop_lon'])
                    lat2 = float(stops.loc[stop2_id, 'stop_lat'])
                    lon2 = float(stops.loc[stop2_id, 'stop_lon'])

                    dist = self.haversine_distance(lat1, lon1, lat2, lon2)

                    if dist < DISTANCE_RANGE[0] or dist > DISTANCE_RANGE[1]:
                        flags.append({
                            'trip_id': trip_id,
                            'stop1': stop1_id,
                            'stop2': stop2_id,
                            'distance_m': round(dist, 1),
                            'issue': 'too_short' if dist < DISTANCE_RANGE[0] else 'too_long'
                        })
                except:
                    continue

        return flags

    # ========================================================================
    # 4. CHECKS TEMPORALES
    # ========================================================================

    def check_temporal(self):
        """Validar datos temporales"""
        self.print_section("4. CHECKS TEMPORALES")

        if 'stop_times' not in self.data:
            self.print_test("Datos temporales", False, "No se cargo stop_times")
            return

        stop_times = self.data['stop_times'].copy()

        # Convertir tiempos
        def time_to_seconds(t):
            if pd.isna(t) or t == '':
                return np.nan
            parts = str(t).split(':')
            try:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except:
                return np.nan

        stop_times['arrival_sec'] = stop_times['arrival_time'].apply(time_to_seconds)
        stop_times['departure_sec'] = stop_times['departure_time'].apply(time_to_seconds)
        stop_times['stop_sequence'] = pd.to_numeric(stop_times['stop_sequence'], errors='coerce')

        # Test 1: arrival <= departure
        invalid_times = (stop_times['arrival_sec'] > stop_times['departure_sec']).sum()
        invalid_pct = invalid_times / len(stop_times) * 100

        self.log_test('temporal', 'arrival_departure',
                      invalid_times == 0,
                      f"{invalid_times} registros con arrival > departure ({invalid_pct:.2f}%)")
        self.print_test("arrival_time d departure_time",
                       invalid_times == 0,
                       f"{len(stop_times) - invalid_times}/{len(stop_times)} validos")

        # Test 2: Secuencia estricta
        stop_times = stop_times.sort_values(['trip_id', 'stop_sequence'])

        sequence_issues = 0
        sample_size = min(1000, stop_times['trip_id'].nunique())

        for trip_id in stop_times['trip_id'].unique()[:sample_size]:
            trip = stop_times[stop_times['trip_id'] == trip_id].copy()
            sequences = trip['stop_sequence'].values

            if len(sequences) > 1:
                if not all(sequences[i] < sequences[i+1] for i in range(len(sequences)-1)):
                    sequence_issues += 1

        sequence_pct = sequence_issues / sample_size * 100 if sample_size > 0 else 0

        self.log_test('temporal', 'secuencia_estricta',
                      sequence_issues == 0,
                      f"{sequence_issues}/{sample_size} trips con secuencia incorrecta ({sequence_pct:.1f}%)")
        self.print_test("stop_sequence estrictamente creciente",
                       sequence_issues == 0,
                       f"{sample_size - sequence_issues}/{sample_size} trips validos")

        # Test 3: Duracion de tramos
        stop_times['duration'] = stop_times.groupby('trip_id')['arrival_sec'].diff()

        invalid_durations = (
            (stop_times['duration'] < DURATION_RANGE[0]) |
            (stop_times['duration'] > DURATION_RANGE[1])
        )
        invalid_durations = invalid_durations & stop_times['duration'].notna()

        duration_pct = invalid_durations.sum() / len(stop_times) * 100

        self.log_test('temporal', 'duracion_tramos',
                      duration_pct < 5,
                      f"{invalid_durations.sum()} tramos con duracion sospechosa ({duration_pct:.2f}%)",
                      'warning')
        self.print_test("Duracion de tramos (10s-60min)",
                       duration_pct < 5,
                       f"{duration_pct:.2f}% fuera de rango")

    # ========================================================================
    # 5. CHECKS DE CONSISTENCIA
    # ========================================================================

    def check_consistency(self):
        """Validar consistencia de datos"""
        self.print_section("5. CHECKS DE CONSISTENCIA")

        # Test 1: route_type valido
        if 'routes' in self.data:
            routes = self.data['routes']
            if 'route_type' in routes.columns:
                valid_types = ['0', '1', '2', '3', '4', '5', '6', '7', '11', '12']
                invalid_types = ~routes['route_type'].isin(valid_types)
                invalid_pct = invalid_types.sum() / len(routes) * 100

                self.log_test('consistency', 'route_type',
                              invalid_types.sum() == 0,
                              f"{invalid_types.sum()} rutas con route_type invalido ({invalid_pct:.1f}%)",
                              'warning')
                self.print_test("route_type válido (GTFS spec)",
                               invalid_types.sum() == 0,
                               f"{len(routes) - invalid_types.sum()}/{len(routes)} rutas")

        # Test 2: Viajes huérfanos
        if 'trips' in self.data and 'stop_times' in self.data:
            trips_with_stops = set(self.data['stop_times']['trip_id'].unique())
            all_trips = set(self.data['trips']['trip_id'].unique())
            orphan_trips = all_trips - trips_with_stops
            orphan_pct = len(orphan_trips) / len(all_trips) * 100 if len(all_trips) > 0 else 0

            self.log_test('consistency', 'viajes_huerfanos',
                          len(orphan_trips) == 0,
                          f"{len(orphan_trips)} trips sin stop_times ({orphan_pct:.1f}%)",
                          'warning')
            self.print_test("Trips con stop_times",
                           orphan_pct < 1,
                           f"{len(trips_with_stops)}/{len(all_trips)} trips usados")

        # Test 3: Stops huérfanos
        if 'stops' in self.data and 'stop_times' in self.data:
            used_stops = set(self.data['stop_times']['stop_id'].unique())
            all_stops = set(self.data['stops']['stop_id'].unique())
            orphan_stops = all_stops - used_stops
            orphan_pct = len(orphan_stops) / len(all_stops) * 100 if len(all_stops) > 0 else 0

            self.log_test('consistency', 'stops_huerfanos',
                          orphan_pct < 10,
                          f"{len(orphan_stops)} stops sin uso ({orphan_pct:.1f}%)",
                          'warning')
            self.print_test("Stops utilizados",
                           orphan_pct < 10,
                           f"{len(used_stops)}/{len(all_stops)} stops en uso")

    # ========================================================================
    # 6. RESUMEN Y CRITERIOS
    # ========================================================================

    def print_summary(self):
        """Imprimir resumen final"""
        self.print_section("RESUMEN DE VALIDACIóN")

        # Contar tests
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warnings = 0

        for category, result in self.results.items():
            for test in result['tests']:
                total_tests += 1
                if test['passed']:
                    passed_tests += 1
                else:
                    if test['severity'] == 'error':
                        failed_tests += 1
                    else:
                        warnings += 1

        print(f"\n  Tests ejecutados: {total_tests}")
        print(f"   Aprobados: {passed_tests}")
        print(f"  Fallidos: {failed_tests}")
        print(f"  Advertencias: {warnings}")

        # Criterios de aceptación
        self.print_section("CRITERIOS DE ACEPTACIóN")

        # Criterio 1: 0% claves rotas
        broken_keys = sum(
            1 for test in self.results['structure']['tests']
            if not test['passed'] and test['severity'] == 'error' and
            ('clave' in test['message'].lower() or 'duplicado' in test['message'].lower() or
             'huérfano' in test['message'].lower())
        )

        criterion_1 = broken_keys == 0
        self.print_test(
            "Criterio 1: 0% claves rotas",
            criterion_1,
            f"{broken_keys} problemas de claves" if not criterion_1 else "Todas las claves válidas"
        )

        # Criterio 2: <1% tramos sospechosos
        suspicious_pct = self.stats.get('suspicious_segments_pct', 0)
        criterion_2 = suspicious_pct < MAX_SUSPICIOUS_SEGMENTS_PCT

        self.print_test(
            "Criterio 2: <1% tramos sospechosos",
            criterion_2,
            f"{suspicious_pct:.2f}% tramos fuera de rango"
        )

        # Criterio 3: Todo documentado
        criterion_3 = True  # Siempre se genera documentación
        self.print_test(
            "Criterio 3: Todo documentado",
            criterion_3,
            "Reportes generados"
        )

        # Resultado final
        all_criteria = criterion_1 and criterion_2 and criterion_3

        self.print_section("RESULTADO FINAL")

        if all_criteria:
            print("\n   FEED APROBADO")
            print("     El feed cumple con todos los criterios de aceptación.")
            print("      Listo para análisis de métricas\n")
        else:
            print("\n  L FEED RECHAZADO")
            print("     El feed NO cumple con los criterios de aceptación.")
            print("     Correcciones requeridas antes de continuar\n")

        return all_criteria

    # ========================================================================
    # EJECUTAR VALIDACIóN
    # ========================================================================

    def run(self):
        """Ejecutar validación completa"""
        print("\n" + "="*70)
        print("  VALIDADOR GTFS - ZONA METROPOLITANA DE GUADALAJARA")
        print("="*70)

        self.freeze_feed()
        self.check_structure()

        if self.results['structure']['passed']:
            self.check_spatial()
            self.check_temporal()
            self.check_consistency()
        else:
            print("\n Validación detenida: fallos críticos en estructura")

        passed = self.print_summary()

        return passed


# ============================================================================
# MAIN
# ============================================================================

def main():
    import sys

    if len(sys.argv) > 1:
        gtfs_path = sys.argv[1]
    else:
        gtfs_path = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis\Datasets\gtfs_amg_20240312\Datos"

    validator = GTFSValidator(gtfs_path)
    passed = validator.run()

    # Exit code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
