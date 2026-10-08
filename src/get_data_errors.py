import osmnx as ox
import geopandas as gpd
import time
import os

os.makedirs("data/hidrografia", exist_ok=True)
os.makedirs("data/centros_poblados", exist_ok=True)

# Municipios con nombre alternativo
nombres_alternativos = {
    '70820': ('Toluviejo', 'Sucre'),  # sin acento ni espacio
}

pendientes = {
    '18592': ('Puerto Rico', 'Caquetá'),
    '66572': ('Pereira', 'Risaralda'),
    '70820': ('Tolú Viejo', 'Sucre'),
}

tags_hidro = {'waterway': ['river', 'stream', 'canal'], 'natural': ['water', 'wetland']}
tags_pob = {'place': ['city', 'town', 'village', 'hamlet', 'neighbourhood']}

for codigo, (municipio, departamento) in pendientes.items():
    # Usar nombre alternativo si existe
    if codigo in nombres_alternativos:
        mun_alt, dep_alt = nombres_alternativos[codigo]
        lugar = f"{mun_alt}, {dep_alt}, Colombia"
    else:
        lugar = f"{municipio}, {departamento}, Colombia"
    
    print(f"\nDescargando: {lugar}")
    time.sleep(2)

    for tipo, tags, carpeta in [
        ('hidrografia', tags_hidro, 'data/hidrografia'),
        ('centros_poblados', tags_pob, 'data/centros_poblados'),
    ]:
        archivo = f"{carpeta}/{codigo}_{municipio}.gpkg"
        if os.path.exists(archivo):
            print(f"  ✓ {tipo} ya existe, saltando")
            continue

        for intento in range(3):
            try:
                gdf = ox.features_from_place(lugar, tags=tags)
                gdf['codigo_municipio'] = codigo
                gdf.to_file(archivo, driver='GPKG')
                print(f"  ✓ {tipo}: {len(gdf)} features")
                break
            except Exception as e:
                if intento < 2:
                    print(f"  intento {intento+1} fallido, esperando 30s...")
                    time.sleep(30)
                else:
                    print(f"  ✗ {tipo} falló: {e}")