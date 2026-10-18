import os
import numpy as np 
import pandas as pd
import osmnx as ox
from backend.grafo_viario import carregar_grafo_bh
from backend.filtro_espacial import FiltroEspacialBH
from backend.geohash import encode
"""
esperado que bares dict seja: 
{
    id: 
    latitude:
    longitude:
}
"""
filtro_bh = FiltroEspacialBH("data/input/limite_municipio.json")

def gerar_entregadores(N: int, bares: dict) -> tuple:
    lat, lon = [], []
    origem_bares = [] 
    
    qtd_bares = len(bares)
    if qtd_bares == 0:
        return np.array([]), np.array([]), []
    
    lista_bares = list(bares.values())
    qtd_entregadores_por_bar = N // qtd_bares 
    resto = N % qtd_bares

    desvio_padrao = 0.008
    
    for i, bar in enumerate(lista_bares):
        tamanho_grupo = qtd_entregadores_por_bar + (1 if i < resto else 0)
        if tamanho_grupo <= 0:
            continue
        lat_bar = bar.get("lat") or bar.get("latitude")
        lon_bar = bar.get("lon") or bar.get("longitude")
        bar_id = bar["id"]
       
        # gera populacao do tamamnho de cada grupo em torno do bar normalmente distribuida em torno da latitude e longitude do bar em questao
        distribuicao_latitude = np.random.normal(loc=lat_bar, scale=desvio_padrao, size=tamanho_grupo)
        distribuicao_longitude = np.random.normal(loc=lon_bar, scale=desvio_padrao, size=tamanho_grupo)
        
        lat.extend(distribuicao_latitude)
        lon.extend(distribuicao_longitude)
        origem_bares.extend([bar["id"]] * tamanho_grupo) # associa cada entregador ao seu bar central

    return np.array(lat), np.array(lon), origem_bares

def corrigir_coordenadas(distribuicao_latitude: np.ndarray, distribuicao_longitude: np.ndarray):
    malha = carregar_grafo_bh()
    coordenadas_corrigidas = ox.distance.nearest_nodes(malha, X=distribuicao_longitude, Y=distribuicao_latitude) # retorna os nós mais próximos das coordenadas dos entregadores
    return malha, coordenadas_corrigidas

def armazenar_dados_entregadores(N: int, bares: dict, caminho_saida="data/output/entregadores_new.csv"):
  lats, lons, origens = gerar_entregadores(N, bares=bares)
  if len(lats) == 0:
    return []

  malha, nos_mais_proximos = corrigir_coordenadas(lats, lons)

  entregadores = []
  for seq_id, (node_id, bar_origem) in enumerate(
      zip(nos_mais_proximos, origens), start=1
  ):
    dados_node = malha.nodes[node_id]

    lat_real = float(dados_node["y"])
    lon_real = float(dados_node["x"])

    # valida se o vertice da rua esta dentro dos limites municipais de BH
    if filtro_bh.ponto_esta_em_bh(lat_real, lon_real):
      entregadores.append({
          "id": seq_id,
          "lat": lat_real,  
          "lon": lon_real,  
          "latitude": lat_real,  
          "longitude": lon_real,  
          "geohash": encode(lat_real, lon_real, 8),
          "id_bar_central": bar_origem,
      })

  os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
  df = pd.DataFrame(entregadores)
  df.to_csv(caminho_saida, index=False, encoding="utf-8")
  print(
      f"[SUCESSO] {len(entregadores)} entregadores validados e salvos em"
      f" {caminho_saida}"
  )

  return entregadores

"""
if __name__ == "__main__":
    # Dicionário de exemplo de bares em Belo Horizonte
    bares_exemplo = {
        1: {
            "id": 1,
            "latitude": -19.9322,
            "longitude": -43.9381
        },
        2: {
            "id": 2,
            "latitude": -19.9392,
            "longitude": -43.9335
        },
        3: {
            "id": 3,
            "latitude": -19.9281,
            "longitude": -43.9405
        }
    }

    print("Iniciando o teste de geração e correção de entregadores...")
    
    # Chama a função principal passando 30 entregadores e os bares de exemplo
    entregadores_gerados = armazenar_dados_entregadores(N=30, bares=bares_exemplo)
    
    if entregadores_gerados:
        print(f"\nTeste concluído com sucesso!")
        print(f"Total de entregadores gerados e corrigidos: {len(entregadores_gerados)}")
        print("Exemplo dos 2 primeiros entregadores:")
        for e in entregadores_gerados[:2]:
            print(e)
"""


