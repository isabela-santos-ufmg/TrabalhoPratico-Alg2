import geopandas as gpd
from shapely.geometry import Point


class BairrosOficiaisBH:

  def __init__(self, caminho_shp="data/input/BAIRRO_OFICIAL.shp"):
    self.coluna_nome = "NOME"  
    try:
      self.gdf = gpd.read_file(caminho_shp)

      if self.gdf.crs != "EPSG:4326":
        self.gdf = self.gdf.to_crs("EPSG:4326")

      print(
          f"[DEBUG] {len(self.gdf)} bairros oficiais de BH carregados com"
          " sucesso."
      )
    except Exception as e:
      print(f"[AVISO] Erro ao carregar shapefile de bairros: {e}")
      self.gdf = None

  def identificar_bairro(self, lat: float, lon: float) -> str:
    if self.gdf is None:
      return "Belo Horizonte"

    ponto = Point(lon, lat)
    match = self.gdf[self.gdf.contains(ponto)]

    if not match.empty:
      return str(match.iloc[0][self.coluna_nome])

    return "Região Metropolitana / Borda"