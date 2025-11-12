import pandas as pd

# Ruta del archivo
ruta = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis\Datasets\gtfs_amg_20240312\Datos\stop_times.csv"

# Cargar stop_times
stop_times = pd.read_csv(ruta, dtype=str)

print("=" * 80)
print("DIAGNÓSTICO DE DUPLICADOS EN stop_times.csv")
print("=" * 80)

# Encontrar duplicados
duplicados_mask = stop_times.duplicated(subset=['trip_id', 'stop_sequence'], keep=False)
duplicados = stop_times[duplicados_mask]

print(f"\nTotal de registros duplicados: {len(duplicados)}")
print(f"Porcentaje: {len(duplicados) / len(stop_times) * 100:.2f}%")

# Mostrar ejemplo específico del trip TL1_01 mencionado en el error
# Aunque el mensaje de error menciona TL1_01, busquemos ejemplos reales
print("\n" + "=" * 80)
print("ANÁLISIS DE PRIMEROS CASOS DUPLICADOS")
print("=" * 80)

# Obtener los primeros trip_ids con duplicados
trips_duplicados = stop_times[duplicados_mask].groupby('trip_id').size().sort_values(ascending=False).head(5)

print(f"\nTop 5 viajes con más duplicados:")
print(trips_duplicados)

# Mostrar un ejemplo completo
primer_trip = trips_duplicados.index[0]
print(f"\n\nEjemplo detallado del viaje: {primer_trip}")
print("-" * 80)
ejemplo = stop_times[stop_times['trip_id'] == primer_trip].sort_values('stop_sequence')
print(ejemplo[['trip_id', 'stop_id', 'stop_sequence', 'arrival_time', 'departure_time']].to_string())

# Verificar si son duplicados exactos o tienen diferencias
print("\n" + "=" * 80)
print("¿SON DUPLICADOS EXACTOS?")
print("=" * 80)

primer_trip_data = stop_times[stop_times['trip_id'] == primer_trip]
duplicados_exactos = primer_trip_data.duplicated(keep=False).sum()
print(f"\nDuplicados exactos (todas las columnas iguales): {duplicados_exactos}")

# Ver cuántas veces aparece cada combinación
print(f"\nCombinaciones (trip_id, stop_sequence) y su frecuencia:")
conteo = stop_times.groupby(['trip_id', 'stop_sequence']).size()
duplicados_conteo = conteo[conteo > 1].sort_values(ascending=False).head(10)
print(duplicados_conteo)

# Guardar reporte completo de duplicados
print("\n" + "=" * 80)
print("GUARDANDO REPORTE DETALLADO")
print("=" * 80)

output_file = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis\Código\etapas\limpieza y validación\duplicados_stop_times.csv"
duplicados.sort_values(['trip_id', 'stop_sequence']).to_csv(output_file, index=False)
print(f"\nReporte guardado en: {output_file}")
print(f"Total de filas duplicadas: {len(duplicados)}")


print("\n" + "=" * 80)
print("CORRECCIÓN DE DUPLICADOS DE TREN LIGERO")
print("=" * 80)

# Máscara para identificar paradas de Tren Ligero (stop_id que empieza con 'MT-')
tren_ligero_mask = stop_times['stop_id'].str.startswith('MT-', na=False)

# Identificar las filas a eliminar: son duplicados Y son de Tren Ligero
filas_a_eliminar_mask = duplicados_mask & tren_ligero_mask

num_a_eliminar = filas_a_eliminar_mask.sum()

if num_a_eliminar > 0:
    print(f"Se eliminarán {num_a_eliminar} registros duplicados de Tren Ligero (stop_id empieza con 'MT-').")

    # Eliminar las filas
    stop_times_corregido = stop_times[~filas_a_eliminar_mask]

    # Guardar el archivo corregido
    ruta_corregida = r"C:\Users\fbetancourt\OneDrive - VINOS AMERICA SA DE CV\Documentos\GitHub\Tesis\Datasets\gtfs_amg_20240312\Datos\stop_times_cleaned.csv"
    stop_times_corregido.to_csv(ruta_corregida, index=False)

    print(f"\nArchivo 'stop_times.csv' corregido guardado como:\n{ruta_corregida}")
    print(f"Registros originales: {len(stop_times)}")
    print(f"Registros después de la limpieza: {len(stop_times_corregido)}")
else:
    print("No se encontraron duplicados de Tren Ligero para eliminar.")