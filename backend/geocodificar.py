import json
import time
import os
import pandas as pd
import osmnx as ox
from backend.geohash import encode

ABREVIACOES = {
    "AVE": "AVENIDA",
    "AL": "ALAMEDA",
    "PC": "PRAÇA",
    "PCA": "PRAÇA",
    "EST": "ESTRADA",
    "ROD": "RODOVIA",
    "TV": "TRAVESSA",
    "BEC": "BECO",
    "LGO": "LARGO",
    "VL": "VILA",
    "CJ": "CONJUNTO",
    "R": "RUA",
}

def expandir_abreviacao(desc_log):
    return ABREVIACOES.get(str(desc_log).upper(), desc_log)

def carregar_cache(arquivo_cache):
    if os.path.exists(arquivo_cache):
        try:
            with open(arquivo_cache, "r", encoding="utf-8") as f:
                cache = json.load(f)
                print(f"[DEBUG] Cache carregado com sucesso: {len(cache)} endereços armazenados.")
                return cache
        except json.JSONDecodeError:
            print("[AVISO] Arquivo de cache corrompido ou vazio. Iniciando cache novo.")
            return {}
    print("[DEBUG] Nenhum arquivo de cache encontrado. Criando novo cache.")
    return {}

def salvar_cache(cache, arquivo_cache):
    os.makedirs(os.path.dirname(arquivo_cache), exist_ok=True)
    with open(arquivo_cache, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def consultar_osmnx_geocode(endereco):
    try:
        print(f"  -> Consultando no OSMNx: {endereco}")
        ponto = ox.geocode(endereco)
        if ponto:
            if isinstance(ponto, (list, tuple)) and len(ponto) >= 2:
                print(f"     [SUCESSO] Coordenadas encontradas: lat={ponto[0]}, lon={ponto[1]}")
                return float(ponto[0]), float(ponto[1])
        print("     [AVISO] Endereço não retornado pelo Nominatim/OSMnx.")
        return None, None
    except Exception as e:
        print(f"     [ERRO na API]: {e}")
        return None, None

def processar_geocodificacao(
    caminho_entrada="data/input/bares.xlsx",
    caminho_saida="data/bares_geohash.csv",
    caminho_cache="data/cache_geo.json"
):
    print(f"[DEBUG] Tentando ler o arquivo de entrada: {caminho_entrada}")
    if not os.path.exists(caminho_entrada):
        print(f"[ERRO CRITICO] O arquivo '{caminho_entrada}' não foi encontrado! Verifique o caminho.")
        return

    df = pd.read_excel(caminho_entrada)

    cache = carregar_cache(caminho_cache)
    novas_coordenadas = 0

    for index, linha in df.iterrows():
        desc_log = str(linha.get("DESC_LOGRADOURO", "") if pd.notna(linha.get("DESC_LOGRADOURO")) else "").strip()
        nome_log = str(linha.get("NOME_LOGRADOURO", "") if pd.notna(linha.get("NOME_LOGRADOURO")) else "").strip()
        numero   = str(linha.get("NUMERO_IMOVEL", "") if pd.notna(linha.get("NUMERO_IMOVEL")) else "").strip()
        bairro   = str(linha.get("NOME_BAIRRO", "") if pd.notna(linha.get("NOME_BAIRRO")) else "").strip()

        end_original = f"{desc_log} {nome_log}, {numero}, {bairro}, Belo Horizonte, MG, Brasil".strip()

        if end_original in cache and cache[end_original].get("lat") is not None:
            continue

        desc_expandido = expandir_abreviacao(desc_log)
        tentativas = [
            end_original,
            f"{desc_expandido} {nome_log}, {numero}, {bairro}, Belo Horizonte, MG, Brasil",
            f"{desc_expandido} {nome_log}, {bairro}, Belo Horizonte, MG, Brasil",
            f"{desc_expandido} {nome_log}, Belo Horizonte, MG, Brasil",
            f"{nome_log}, {bairro}, Belo Horizonte, MG, Brasil",
        ]

        lat, lon = None, None
        for tentativa in tentativas:
            lat, lon = consultar_osmnx_geocode(tentativa)
            time.sleep(1.0) 
            if lat is not None:
                break

        cache[end_original] = {"lat": lat, "lon": lon}
        salvar_cache(cache, caminho_cache)
        if lat is not None:
            novas_coordenadas += 1

    print(f"[DEBUG] Processamento de geocodificação concluído. Novas coordenadas obtidas nesta execução: {novas_coordenadas}")
    print("[DEBUG] Montando DataFrame de saída...")

    lats, lons, geohashes, enderecos_consultados = [], [], [], []

    for _, linha in df.iterrows():
        desc_log = str(linha.get("DESC_LOGRADOURO", "") if pd.notna(linha.get("DESC_LOGRADOURO")) else "").strip()
        nome_log = str(linha.get("NOME_LOGRADOURO", "") if pd.notna(linha.get("NOME_LOGRADOURO")) else "").strip()
        numero   = str(linha.get("NUMERO_IMOVEL", "") if pd.notna(linha.get("NUMERO_IMOVEL")) else "").strip()
        bairro   = str(linha.get("NOME_BAIRRO", "") if pd.notna(linha.get("NOME_BAIRRO")) else "").strip()
        end_original = f"{desc_log} {nome_log}, {numero}, {bairro}, Belo Horizonte, MG, Brasil".strip()

        res = cache.get(end_original, {})
        lat, lon = res.get("lat"), res.get("lon")
        geohash = encode(lat, lon, 8) if (lat is not None and lon is not None) else ""

        lats.append(lat)
        lons.append(lon)
        geohashes.append(geohash)
        enderecos_consultados.append(end_original)

    df["LATITUDE"] = lats
    df["LONGITUDE"] = lons
    df["GEOHASH"] = geohashes
    df["ENDERECO_CONSULTADO"] = enderecos_consultados

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)

    if caminho_saida.endswith(".csv"):
        df.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
    else:
        df.to_excel(caminho_saida, index=False)

    print(f"[SUCESSO] Arquivo gerado e salvo em: {caminho_saida}")

if __name__ == "__main__":
    processar_geocodificacao()