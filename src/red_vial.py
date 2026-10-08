import osmnx as ox
import geopandas as gpd
import os
import time
import sys
from pathlib import Path
from tqdm import tqdm

# ============================================================
# PATHS — ajusta según tu estructura
# ============================================================
PATH_MUNICIPIOS  = "../data/Municipios_Diciembre_2025_shp/Munpio.shp"
PATH_GEOJSON     = "../data/Processed/full_MIG.geojson"
PATH_OUTPUT      = "../data/red_vial_osm/"
# ============================================================

os.makedirs(PATH_OUTPUT, exist_ok=True)

# Cargar municipios
print("Cargando municipios...")
municipios = gpd.read_file(PATH_MUNICIPIOS)
municipios['MpCodigo'] = municipios['MpCodigo'].astype(str).str.zfill(5)
municipios = municipios.to_crs("EPSG:4326")

# Cargar códigos de municipios con diligencias
import json
with open(PATH_GEOJSON) as f:
    data = json.load(f)
props = [f['properties'] for f in data['features']]
import pandas as pd
df = pd.DataFrame(props)
codigos = [c for c in df['Cod_Mun'].astype(str).str.zfill(5).unique() 
           if c != '000SD']

print(f"Municipios a procesar: {len(codigos)}")

errores = []
for i, codigo in tqdm(enumerate(codigos), total=len(codigos)):
    archivo = Path(PATH_OUTPUT) / f"{codigo}_vias.gpkg"
    
    if archivo.exists():
        print(f"[{i+1}/{len(codigos)}] {codigo}: ya existe, saltando")
        continue

    mun = municipios[municipios['MpCodigo'] == codigo]
    if len(mun) == 0:
        print(f"[{i+1}/{len(codigos)}] {codigo}: municipio no encontrado")
        continue

    print(f"[{i+1}/{len(codigos)}] Descargando: {codigo}")

    for intento in range(3):
        try:
            G = ox.graph_from_polygon(
                mun.geometry.values[0],
                network_type='all'
            )
            vias = ox.graph_to_gdfs(G, nodes=False)
            vias.to_file(archivo, driver='GPKG')
            print(f"  ✓ {len(vias)} segmentos")
            time.sleep(1)
            break

        except Exception as e:
            if intento < 2:
                print(f"  intento {intento+1} fallido, esperando 15s...")
                time.sleep(15)
            else:
                print(f"  ✗ Error: {e}")
                errores.append((codigo, str(e)))

print(f"\n{'='*50}")
print(f"Completado.")
print(f"Errores: {len(errores)}")
for cod, err in errores:
    print(f"  {cod}: {err}")