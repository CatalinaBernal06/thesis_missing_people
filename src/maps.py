import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
import rasterio
from rasterio.transform import from_bounds
PATH_PROCESSED="../data/Processed/"


def build_mapa_calor(cod_mun, modelo_final, nom_modelo, X, grupos, municipios):
    codigo = cod_mun
    print(f"Generando mapa de probabilidades para {codigo}...")

    # Cargar geometría del municipio
    mun = municipios[municipios['MpCodigo'] == codigo]
    bounds = mun.total_bounds  # minx, miny, maxx, maxy

    # Cargar rasters
    ndvi_path = Path("../data/landsat/landsat_ndvi/") / f"ndvi_{codigo}.tif"
    dem_path  = Path("../data/dem/dem_srtm/") / f"dem_{codigo}.tif"

    # Definir grid de predicción
    resolucion_grados = 30 / 111320
    width  = int((bounds[2] - bounds[0]) / resolucion_grados)
    height = int((bounds[3] - bounds[1]) / resolucion_grados)

    # Limitar tamaño para no saturar memoria
    max_dim = 300
    if width > max_dim or height > max_dim:
        factor = max(width, height) / max_dim
        width  = int(width / factor)
        height = int(height / factor)

    print(f"Grid de predicción: {height} x {width}")

    # Construir grid de coordenadas
    lons = np.linspace(bounds[0], bounds[2], width)
    lats = np.linspace(bounds[3], bounds[1], height)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # Extraer covariables para cada punto del grid
    print("Extrayendo covariables del grid...")
    X_grid = np.zeros((height * width, 6))
    X_grid[:] = np.nan

    coords_flat = list(zip(lon_grid.flatten(), lat_grid.flatten()))

    # NDVI
    with rasterio.open(ndvi_path) as src:
        ndvi_vals = np.array([v[0] for v in src.sample(coords_flat)], dtype=float)
        ndvi_vals[ndvi_vals == src.nodata] = np.nan

    # DEM
    with rasterio.open(dem_path) as src:
        dem_vals = np.array([v[0] for v in src.sample(coords_flat)], dtype=float)
        dem_vals[dem_vals == src.nodata] = np.nan

    # Pendiente aproximada
    delta = 0.001
    coords_e = [(lon + delta, lat) for lon, lat in coords_flat]
    coords_n = [(lon, lat + delta) for lon, lat in coords_flat]
    with rasterio.open(dem_path) as src:
        dem_e = np.array([v[0] for v in src.sample(coords_e)], dtype=float)
        dem_n = np.array([v[0] for v in src.sample(coords_n)], dtype=float)

    dz_dx = (dem_e - dem_vals) / (delta * 111320)
    dz_dy = (dem_n - dem_vals) / (delta * 111320)
    slope_vals = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))

    # Cargar stack para distancias
    stack = np.load(Path(PATH_PROCESSED) / f"covariables_{codigo}.npy")
    h_stack, w_stack = stack.shape[1], stack.shape[2]

    def coord_a_pixel(lon, lat):
        col = int((lon - bounds[0]) / (bounds[2] - bounds[0]) * w_stack)
        row = int((bounds[3] - lat) / (bounds[3] - bounds[1]) * h_stack)
        return np.clip(row, 0, h_stack-1), np.clip(col, 0, w_stack-1)

    dist_hidro = np.array([
        stack[3, *coord_a_pixel(lon, lat)] 
        for lon, lat in coords_flat
    ])
    dist_vias = np.array([
        stack[4, *coord_a_pixel(lon, lat)] 
        for lon, lat in coords_flat
    ])
    dist_pob = np.array([
        stack[5, *coord_a_pixel(lon, lat)] 
        for lon, lat in coords_flat
    ])
    dist_refs = np.array([
        stack[6, *coord_a_pixel(lon, lat)] 
        for lon, lat in coords_flat
    ])

    # Ensamblar covariables — 7 columnas
    X_grid = np.zeros((height * width, 7))
    X_grid[:] = np.nan
    X_grid[:, 0] = ndvi_vals
    X_grid[:, 1] = dem_vals
    X_grid[:, 2] = slope_vals
    X_grid[:, 3] = dist_hidro
    X_grid[:, 4] = dist_vias
    X_grid[:, 5] = dist_pob
    X_grid[:, 6] = dist_refs

    # Imputar NaN con mediana del municipio en entrenamiento
    idx_mun = grupos == codigo
    X_mun = X[idx_mun]
    for i in range(X_grid.shape[1]):
        nan_mask = np.isnan(X_grid[:, i])
        if nan_mask.sum() > 0:
            X_grid[nan_mask, i] = np.nanmedian(X_mun[:, i])

    # Predecir
    print("Prediciendo probabilidades...")
    pi_flat = modelo_final.predict_proba(X_grid)
    pi_grid = pi_flat.reshape(height, width)

    # Máscara del municipio
    from rasterio.features import geometry_mask
    from rasterio.transform import from_bounds as fb

    transform = fb(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
    mask = geometry_mask(
        [mun.geometry.values[0].__geo_interface__],
        transform=transform,
        invert=True,
        out_shape=(height, width)
    )
    pi_grid[~mask] = np.nan

    # ============================================================
    # MAPA
    # ============================================================
    verde       = '#1B5E3B'
    dorado      = '#C8A951'
    verde_claro = '#74C69D'

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor('#E8F4F8')
    fig.patch.set_facecolor('white')

    # Mapa de calor
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'fosas', ['#F5F5F0', '#97C98F', '#4A8C5C', '#1B5E3B', '#0A2E1A']
    )

    im = ax.imshow(
        pi_grid,
        extent=[bounds[0], bounds[2], bounds[1], bounds[3]],
        cmap=cmap, vmin=0, vmax=1,
        origin='upper', alpha=0.85
    )

    # Contorno del municipio
    mun.boundary.plot(ax=ax, color='#333', linewidth=1.5)

    # Puntos de presencias conocidas
    pres = gpd.GeoDataFrame(
        pd.read_csv(Path(PATH_PROCESSED) / f"presencias_{codigo}.csv"),
        geometry=gpd.points_from_xy(
            pd.read_csv(Path(PATH_PROCESSED) / f"presencias_{codigo}.csv")['lon'],
            pd.read_csv(Path(PATH_PROCESSED) / f"presencias_{codigo}.csv")['lat']
        ),
        crs="EPSG:4326"
    )
    pres.plot(ax=ax, color='red', markersize=25, 
            alpha=0.9, zorder=5, label='Exhumaciones confirmadas')

    # Colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Probabilidad de presencia $\\hat{\\pi}_i$', 
                fontsize=10, color='#333')
    cbar.ax.tick_params(colors='#666')

    # Títulos y leyenda
    ax.set_title(
        f'Mapa de calor — {codigo}\nModelo {nom_modelo}',
        fontsize=13, pad=15, color='#1a1a1a'
    )
    ax.legend(fontsize=10, loc='lower right', framealpha=0.95)
    ax.set_xlabel('Longitud', fontsize=10, color='#555')
    ax.set_ylabel('Latitud', fontsize=10, color='#555')

    ax.text(0.01, 0.01,
            f'Fuente: EQUITAS Colombia. Modelo: {nom_modelo}. Elaboración propia.',
            transform=ax.transAxes, fontsize=7.5, color='#999', style='italic')

    plt.tight_layout()
    plt.savefig(f'../data/Processed/mapa_calor_{codigo}_{nom_modelo}.png',
                dpi=200, bbox_inches='tight', facecolor='white')
    plt.show()
    print("✓ Mapa guardado")