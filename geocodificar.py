"""
Geocodificação dos endereços da planilha bares.xlsx usando Nominatim (OpenStreetMap).

O script:
  1. Lê o bares.xlsx
  2. Consulta lat/lon de cada endereço único no Nominatim (1 req/s)
  3. Salva o progresso em cache_geo.json a cada resultado
  4. Calcula o Geohash com nossa função encode()
  5. Grava o resultado em bares_com_geohash.xlsx

Pode ser interrompido e retomado: o cache evita reconsultar endereços já obtidos.
"""

import json
import time
import openpyxl
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geohash import encode as geohash_encode

# -----------------------------------------------------------------------
# Configurações
# -----------------------------------------------------------------------

ARQUIVO_ENTRADA  = "bares.xlsx"
ARQUIVO_SAIDA    = "bares_com_geohash.xlsx"
ARQUIVO_CACHE    = "cache_geo.json"
PRECISAO_GEOHASH = 8
PAUSA_SEGUNDOS   = 1.1   # Nominatim exige no mínimo 1 req/s; usamos 1.1 para folga

# -----------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------

def montar_endereco(row):
    """
    Monta a string de endereço a partir das colunas da planilha.
    row é uma tupla com os valores na ordem das colunas do Excel.
    """
    desc_log = str(row[3] or "")   # DESC_LOGRADOURO  (ex: "RUA", "AVE")
    nome_log = str(row[4] or "")   # NOME_LOGRADOURO  (ex: "DO OURO")
    numero   = str(row[5] or "")   # NUMERO_IMOVEL
    bairro   = str(row[7] or "")   # NOME_BAIRRO

    return f"{desc_log} {nome_log}, {numero}, {bairro}, Belo Horizonte, MG, Brasil".strip()


def carregar_cache():
    """Carrega os resultados já obtidos de execuções anteriores."""
    try:
        with open(ARQUIVO_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def salvar_cache(cache):
    """Grava o cache em disco após cada consulta."""
    with open(ARQUIVO_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def consultar_nominatim(geolocator, endereco):
    """
    Consulta o Nominatim para um endereço.
    Retorna (latitude, longitude) ou (None, None) se não encontrar.
    """
    try:
        resultado = geolocator.geocode(endereco, timeout=10)
        if resultado:
            return resultado.latitude, resultado.longitude
        return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"  ERRO na consulta: {e}")
        return None, None


# -----------------------------------------------------------------------
# Etapa 1 — Ler a planilha
# -----------------------------------------------------------------------

print("Lendo a planilha...")
wb_entrada = openpyxl.load_workbook(ARQUIVO_ENTRADA, read_only=True, data_only=True)
ws_entrada = wb_entrada.active

todas_as_linhas = list(ws_entrada.iter_rows(values_only=True))
cabecalho = todas_as_linhas[0]
dados = todas_as_linhas[1:]

print(f"  {len(dados)} registros encontrados.")
wb_entrada.close()

# -----------------------------------------------------------------------
# Etapa 2 — Identificar endereços únicos
# -----------------------------------------------------------------------

# Monta a lista de endereços mantendo a posição de cada linha
enderecos_por_linha = [montar_endereco(row) for row in dados]
enderecos_unicos = list(set(enderecos_por_linha))

print(f"  {len(enderecos_unicos)} endereços únicos para consultar.")

# -----------------------------------------------------------------------
# Etapa 3 — Geocodificação com cache
# -----------------------------------------------------------------------

cache = carregar_cache()
ja_consultados = len([e for e in enderecos_unicos if e in cache])
faltam = len(enderecos_unicos) - ja_consultados

print(f"\nCache existente: {ja_consultados} endereços já consultados.")
print(f"Faltam consultar: {faltam} endereços.")

if faltam > 0:
    horas_estimadas = round(faltam * PAUSA_SEGUNDOS / 3600, 1)
    print(f"Tempo estimado: ~{horas_estimadas} horas.\n")

    geolocator = Nominatim(user_agent="tp_alg2_bh_geohash")

    consultados = 0
    for endereco in enderecos_unicos:
        if endereco in cache:
            continue   # já temos o resultado, pula

        lat, lon = consultar_nominatim(geolocator, endereco)
        cache[endereco] = {"lat": lat, "lon": lon}
        salvar_cache(cache)

        consultados += 1
        status = f"lat={lat:.5f}, lon={lon:.5f}" if lat else "não encontrado"
        print(f"  [{consultados}/{faltam}] {status} | {endereco[:60]}")

        time.sleep(PAUSA_SEGUNDOS)

    print("\nGeocodificação concluída.")
else:
    print("Todos os endereços já estão no cache. Pulando geocodificação.\n")

# -----------------------------------------------------------------------
# Etapa 4 — Montar a planilha de saída
# -----------------------------------------------------------------------

print("Montando o arquivo de saída...")

wb_saida = openpyxl.Workbook()
ws_saida = wb_saida.active
ws_saida.title = "Resultado"

# Cabeçalho: colunas originais + três novas
ws_saida.append(list(cabecalho) + ["LATITUDE", "LONGITUDE", "GEOHASH", "ENDERECO_CONSULTADO"])

sem_coordenada = 0

for i, row in enumerate(dados):
    endereco = enderecos_por_linha[i]
    resultado = cache.get(endereco, {})
    lat = resultado.get("lat")
    lon = resultado.get("lon")

    if lat is not None and lon is not None:
        geohash = geohash_encode(lat, lon, PRECISAO_GEOHASH)
    else:
        geohash = ""
        sem_coordenada += 1

    ws_saida.append(list(row) + [lat, lon, geohash, endereco])

wb_saida.save(ARQUIVO_SAIDA)
print(f"Arquivo salvo: {ARQUIVO_SAIDA}")
print(f"  Registros com Geohash: {len(dados) - sem_coordenada}")
print(f"  Registros sem coordenada: {sem_coordenada}")
