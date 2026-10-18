import geopandas as gpd
from shapely.geometry import Point

class FiltroEspacialBH:
    def __init__(self, caminho_json="data/input/limite_municipio.json"):
        try:
            self.gdf_limite = gpd.read_file(caminho_json)
            
            if self.gdf_limite.crs != "EPSG:4326":
                self.gdf_limite = self.gdf_limite.to_crs("EPSG:4326")
                
            self.poligono_bh = self.gdf_limite.unary_union
            print("[DEBUG] Limite municipal de BH carregado do arquivo JSON com sucesso.")
        except Exception as e:
            print(f"[AVISO] Não foi possível carregar o arquivo JSON de limite: {e}. Validação espacial desativada.")
            self.poligono_bh = None

    def ponto_esta_em_bh(self, lat: float, lon: float) -> bool:
        if self.poligono_bh is None:
            return True 
        ponto = Point(lon, lat)
        return self.poligono_bh.contains(ponto)