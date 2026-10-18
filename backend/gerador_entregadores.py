import os
from backend.filtro_espacial import FiltroEspacialBH
from backend.geohash import encode
from backend.grafo_viario import carregar_grafo_bh
import numpy as np
import osmnx as ox
import pandas as pd

filtro_bh = FiltroEspacialBH("data/input/limite_municipio.json")


def gerar_entregadores(N: int, bares: dict) -> tuple:
  lat, lon = [], []
  origem_bares = []

  qtd_bares = len(bares)
  if qtd_bares == 0:
    return np.array([]), np.array([]), []

  lista_bares = list(bares.values())
  desvio_padrao = 0.008  

  if N < qtd_bares:
    indices_escolhidos = np.random.choice(qtd_bares, size=N, replace=False)
    bares_alvo = [lista_bares[i] for i in indices_escolhidos]
    qtd_entregadores_por_bar = 1
    resto = 0
  else:
    bares_alvo = lista_bares
    qtd_entregadores_por_bar = N // qtd_bares
    resto = N % qtd_bares

  for i, bar in enumerate(bares_alvo):
    tamanho_grupo = qtd_entregadores_por_bar + (1 if i < resto else 0)
    if tamanho_grupo <= 0:
      continue

    lat_bar = bar.get("lat") or bar.get("latitude")
    lon_bar = bar.get("lon") or bar.get("longitude")
    bar_id = bar["id"]

    distribuicao_latitude = np.random.normal(loc=lat_bar, scale=desvio_padrao, size=tamanho_grupo)
    distribuicao_longitude = np.random.normal(loc=lon_bar, scale=desvio_padrao, size=tamanho_grupo)

    lat.extend(distribuicao_latitude)
    lon.extend(distribuicao_longitude)
    origem_bares.extend([bar_id] * tamanho_grupo)

  return np.array(lat), np.array(lon), origem_bares


def corrigir_coordenadas(
    distribuicao_latitude: np.ndarray, distribuicao_longitude: np.ndarray
):
  malha = carregar_grafo_bh()
  coordenadas_corrigidas = ox.distance.nearest_nodes(malha, X=distribuicao_longitude, Y=distribuicao_latitude)
  return malha, coordenadas_corrigidas


def armazenar_dados_entregadores(
    N: int, bares: dict, caminho_saida="data/output/entregadores_new.csv"
):
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
      f"[SUCESSO] Exatamente {len(entregadores)} entregadores validados e salvos"
      f" em {caminho_saida}"
  )

  return entregadores