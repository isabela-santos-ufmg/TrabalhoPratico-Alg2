# Local: Belo Horizonte, Minas Gerais, Região Sudeste, Brasil (-20.05946 -44.06329 -19.77654 -43.85722)
from collections import Counter
import os
import re
import unicodedata
from backend.bairros import BairrosOficiaisBH
from backend.geohash import encode
from backend.grafo_viario import carregar_grafo_bh
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

"""
Na malha, alguns nomes contém grafia diferente do oficial dado pelo openstreetmap, 
causando erros captados pelo debug. Este dicionário serve para mapear nomes incorretos para os corretos, evitando erros de geocodificação.
"""
DE_PARA_BH = {
    "BERNARDO DE VASCONCELOS": "BERNARDO MONTEIRO DE VASCONCELOS",
    "PROFESSOR MORAES": "PROFESSOR MORAIS",
    "CHRISTINA MARIA ASSIS": "CRISTINA MARIA DE ASSIS",
    "KIMBERLITA": "QUIMBERLITA",
    "PARANA": "PARANA",
    "JOSE DE PATROCINIO PONTES": "JOSE DO PATROCINIO PONTES",
    "INACIO PARREIRA NEVES": "INACIO PARREIRAS NEVES",
    "CAISSARA": "CAICARA",
}

BH_LAT_MIN, BH_LAT_MAX = -20.06, -19.75
BH_LON_MIN, BH_LON_MAX = -44.06, -43.85

SINONIMOS_TITULOS = {
    r"\bDR\b": "DOUTOR",
    r"\bDRA\b": "DOUTORA",
    r"\bPE\b": "PADRE",
    r"\bSTA\b": "SANTA",
    r"\bSTO\b": "SANTO",
    r"\bS\b": "SAO",
    r"\bPROF\b": "PROFESSOR",
    r"\bPROFA\b": "PROFESSORA",
    r"\bCEL\b": "CORONEL",
    r"\bGEN\b": "GENERAL",
    r"\bMAJ\b": "MAJOR",
    r"\bCAP\b": "CAPITAO",
    r"\bSGT\b": "SARGENTO",
    r"\bTEN\b": "TENENTE",
    r"\bPRES\b": "PRESIDENTE",
    r"\bGOV\b": "GOVERNADOR",
    r"\bENG\b": "ENGENHEIRO",
    r"\bDES\b": "DESEMBARGADOR",
    r"\bSEN\b": "SENADOR",
    r"\bDEPUTADO\b": "DEP",
}


def normalizar_texto(texto):
  if not texto or pd.isna(texto):
    return ""
  texto = str(texto).upper().strip()

  # remover acentos
  texto = unicodedata.normalize("NFKD", texto)
  texto = "".join(c for c in texto if not unicodedata.combining(c))

  # considera dicionario de nomes incorretos para nomes corretos
  for errado, certo in DE_PARA_BH.items():
    if errado in texto:
      texto = texto.replace(errado, certo)

  # expande abreviações de títulos e prefixos
  for abrev, exp in SINONIMOS_TITULOS.items():
    texto = re.sub(abrev, exp, texto)

  
  texto = re.sub(
      r"\b(RUA|AVENIDA|AVE|ALAMEDA|AL|PRACA|PCA|ESTRADA|ROD|RODOVIA|TRAVESSA|TV|BECO|BEC|LARGO|LGO|VILA|VL|CONJUNTO|CJ)\b",
      "",
      texto,
  )
  texto = re.sub(r"[^\w\s]", "", texto)
  return " ".join(texto.split())


def construir_indice_vias(grafo):
  print("[1/5] Carregando e indexando malha viária do OSMnx...")
  vias_map = {}

  for u, v, k, dados in grafo.edges(keys=True, data=True):
    nome = dados.get("name")
    if not nome:
      continue

    nomes = nome if isinstance(nome, list) else [nome]

    if "geometry" in dados:
      geom = dados["geometry"]
    else:
      p1 = (grafo.nodes[u]["x"], grafo.nodes[u]["y"])
      p2 = (grafo.nodes[v]["x"], grafo.nodes[v]["y"])
      geom = LineString([p1, p2])

    for n in nomes:
      chave = normalizar_texto(n)
      if chave:
        vias_map.setdefault(chave, []).append(geom)

  print(
      f"[2/5] Consolidando {len(vias_map)} eixos viários em linhas contínuas..."
  )
  vias_consolidadas = {}
  for nome_norm, lista_geoms in vias_map.items():
    try:
      uniao = linemerge(lista_geoms)
      if isinstance(uniao, (LineString, MultiLineString)):
        vias_consolidadas[nome_norm] = uniao
    except Exception:
      continue

  return vias_consolidadas


def extrair_numero(valor):
  if pd.isna(valor):
    return None
  nums = re.findall(r"\d+", str(valor))
  return float(nums[0]) if nums else None


def geocodificar_offline(
    caminho_entrada="data/input/bares.xlsx",
    caminho_saida="data/output/bares_com_geohash.xlsx",
):

  if not os.path.exists(caminho_entrada):
    print(f"[ERRO CRÍTICO] Arquivo '{caminho_entrada}' não encontrado!")
    return

  grafo = carregar_grafo_bh()
  vias_index = construir_indice_vias(grafo)
  bairros_oficiais = BairrosOficiaisBH("data/input/BAIRRO_OFICIAL.shp")

  centroides_bairros = {}
  if bairros_oficiais.gdf is not None:
    for _, linha in bairros_oficiais.gdf.iterrows():
      nome_b = normalizar_texto(linha["NOME"])
      ponto_c = linha.geometry.centroid
      centroides_bairros[nome_b] = (ponto_c.y, ponto_c.x)

  print(f"[3/5] Lendo base de bares: {caminho_entrada}...")
  df = pd.read_excel(caminho_entrada)
  total = len(df)

  print(f"[4/5] Processando {total} bares com múltiplas estratégias...")

  lats, lons, geohashes, metodos = [], [], [], []
  ruas_nao_encontradas = []
  fora_de_bh = 0
  contagem_metodos = Counter()

  for idx, linha in df.iterrows():
    nome_log_raw = str(linha.get("NOME_LOGRADOURO", "")).strip()
    nome_log = normalizar_texto(nome_log_raw)
    desc_log = normalizar_texto(linha.get("DESC_LOGRADOURO", ""))
    bairro_raw = normalizar_texto(linha.get("NOME_BAIRRO", ""))
    num_predial = extrair_numero(linha.get("NUMERO_IMOVEL"))

    # busca direta do nome da rua
    linha_rua = vias_index.get(nome_log)

    # busca com o tipo composto 
    if linha_rua is None:
      linha_rua = vias_index.get(f"{desc_log} {nome_log}".strip())

    # busca por token se for nome composto
    if linha_rua is None and len(nome_log.split()) > 1:
      for chave_via in vias_index:
        if chave_via.endswith(nome_log) or nome_log.endswith(chave_via):
          linha_rua = vias_index[chave_via]
          break

    lat, lon, metodo = None, None, "NAO_LOCALIZADO"

    if linha_rua is not None and not linha_rua.is_empty:
      comprimento = linha_rua.length

      if num_predial and num_predial > 0:
        dist_graus = num_predial / 111320.0
        if dist_graus < comprimento:
          ponto = linha_rua.interpolate(dist_graus)
        else:
          ponto = linha_rua.interpolate(0.95, normalized=True)
        metodo = "NUMERO_PREDIAL"
      else:
        ponto = linha_rua.interpolate(0.5, normalized=True)
        metodo = "MEIO_DA_VIA"

      lon, lat = ponto.x, ponto.y

    elif bairro_raw in centroides_bairros:
      lat, lon = centroides_bairros[bairro_raw]
      metodo = "CENTROIDE_BAIRRO"
    else:
      ruas_nao_encontradas.append(
          f"{nome_log_raw} (Bairro: {linha.get('NOME_BAIRRO', 'N/D')})"
      )

    if lat and lon:
      if not (
          BH_LAT_MIN <= lat <= BH_LAT_MAX and BH_LON_MIN <= lon <= BH_LON_MAX
      ):
        fora_de_bh += 1

    gh = encode(lat, lon, 8) if (lat and lon) else ""
    lats.append(lat)
    lons.append(lon)
    geohashes.append(gh)
    metodos.append(metodo)
    contagem_metodos[metodo] += 1

  df["LATITUDE"] = lats
  df["LONGITUDE"] = lons
  df["GEOHASH"] = geohashes
  df["METODO_GEOCOD"] = metodos

  df_valido = df.dropna(subset=["LATITUDE", "LONGITUDE"])

  os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
  if caminho_saida.endswith(".xlsx"):
    df_valido.to_excel(caminho_saida, index=False)
  else:
    df_valido.to_csv(caminho_saida, index=False, encoding="utf-8-sig")

  # ---- DEBUG ------
  print("\n" + "=" * 60)
  print("              RELATÓRIO DE AUDITORIA GEOESPACIAL           ")
  print("=" * 60)
  print(f"Total de bares na base original : {total}")
  print(
      f"Bares localizados com sucesso   : {len(df_valido)}"
      f" ({len(df_valido)/total*100:.2f}%)"
  )
  print(f"Bares fora do polígono de BH    : {fora_de_bh} (Esperado: 0)")
  print("\nDetalhamento por Método de Resolução:")
  for metodo, qtd in contagem_metodos.items():
    print(f"  - {metodo:<20}: {qtd:>6} ({qtd/total*100:>5.1f}%)")

  if ruas_nao_encontradas:
    print("\nTop 15 Ruas/Locais mais frequentes que NÃO foram localizados:")
    mais_comuns = Counter(ruas_nao_encontradas).most_common(15)
    for rua, frequencia in mais_comuns:
      print(f"  [{frequencia:>3}x] {rua}")

  print("=" * 60)
  print(f"[SUCESSO] Base final exportada para: {caminho_saida}\n")


if __name__ == "__main__":
  geocodificar_offline()