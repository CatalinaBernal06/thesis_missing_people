import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path
import os

# Crear carpetas con ruta absoluta
os.makedirs("data/hidrografia", exist_ok=True)
os.makedirs("data/centros_poblados", exist_ok=True)

# Verificar que se crearon
print("Carpetas creadas en:", os.path.abspath("data"))

# Diccionario código -> (municipio, departamento)
municipios = {
    '05034': ('Arboletes', 'Antioquia'),
    '05042': ('Amalfi', 'Antioquia'),
    '05093': ('Betulia', 'Antioquia'),
    '05107': ('Briceño', 'Antioquia'),
    '05113': ('Campamento', 'Antioquia'),
    '05120': ('Cáceres', 'Antioquia'),
    '05154': ('Caracolí', 'Antioquia'),
    '05361': ('Ituango', 'Antioquia'),
    '05411': ('Maceo', 'Antioquia'),
    '05501': ('Nechí', 'Antioquia'),
    '05543': ('Peñol', 'Antioquia'),
    '05579': ('Remedios', 'Antioquia'),
    '05628': ('San Carlos', 'Antioquia'),
    '05647': ('San Roque', 'Antioquia'),
    '05652': ('San Francisco', 'Antioquia'),
    '05819': ('Toledo', 'Antioquia'),
    '05854': ('Valdivia', 'Antioquia'),
    '05887': ('Zaragoza', 'Antioquia'),
    '17380': ('La Dorada', 'Caldas'),
    '17444': ('Manzanares', 'Caldas'),
    '17495': ('Norcasia', 'Caldas'),
    '17614': ('Riosucio', 'Caldas'),
    '17662': ('Samaná', 'Caldas'),
    '17867': ('Viterbo', 'Caldas'),
    '18592': ('Puerto Rico', 'Caquetá'),
    '20238': ('El Paso', 'Cesar'),
    '47170': ('Chivolo', 'Magdalena'),
    '50350': ('La Macarena', 'Meta'),
    '50711': ('San Juanito', 'Meta'),
    '54206': ('Convención', 'Norte de Santander'),
    '54250': ('El Carmen', 'Norte de Santander'),
    '54720': ('Sardinata', 'Norte de Santander'),
    '54810': ('Teorama', 'Norte de Santander'),
    '66456': ('Marsella', 'Risaralda'),
    '66572': ('Pereira', 'Risaralda'),
    '70001': ('Sincelejo', 'Sucre'),
    '70429': ('Morroa', 'Sucre'),
    '70713': ('San Onofre', 'Sucre'),
    '70820': ('Tolú Viejo', 'Sucre'),
}

errores = []

for codigo, (municipio, departamento) in municipios.items():
    lugar = f"{municipio}, {departamento}, Colombia"
    print(f"Descargando: {lugar}")
    
    try:
        # Hidrografía
        hidro = ox.features_from_place(
            lugar,
            tags={'waterway': ['river', 'stream', 'canal'],
                  'natural': ['water', 'wetland']}
        )
        hidro['codigo_municipio'] = codigo
        hidro.to_file(
            f"data/hidrografia/{codigo}_{municipio}.gpkg",
            driver='GPKG'
        )
        print(f"  ✓ Hidrografía: {len(hidro)} features")

    except Exception as e:
        print(f"  ✗ Hidrografía error: {e}")
        errores.append((codigo, municipio, 'hidrografia', str(e)))

    try:
        # Centros poblados
        poblados = ox.features_from_place(
            lugar,
            tags={'place': ['city', 'town', 'village', 'hamlet',
                            'neighbourhood']}
        )
        poblados['codigo_municipio'] = codigo
        poblados.to_file(
            f"data/centros_poblados/{codigo}_{municipio}.gpkg",
            driver='GPKG'
        )
        print(f"  ✓ Centros poblados: {len(poblados)} features")

    except Exception as e:
        print(f"  ✗ Centros poblados error: {e}")
        errores.append((codigo, municipio, 'centros_poblados', str(e)))

# Reporte final
print(f"\n{'='*50}")
print(f"Descarga completada")
print(f"Errores: {len(errores)}")
if errores:
    for e in errores:
        print(f"  - {e[1]} ({e[0]}): {e[2]}")