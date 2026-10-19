"""
Script de experimentos - Seção 6 do relatório.
Executa as 5 consultas definidas na Seção 6.2 e coleta os tempos reais.

Execute com:
    python experimentos.py

Os resultados são exibidos no terminal e salvos em data/output/experimentos.txt
"""
import sys
import os
import time

import numpy as np

# Garante que os imports do backend funcionem a partir da raiz do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SEMENTE = 42
REPETICOES = 3  # Repetições para calcular média e desvio padrão

from backend.bares import carregar_bares
from backend.geohash import encode, haversine, decode_geohash, vizinhos
from backend.trie_and_geohash import construir_trie, buscar_entregadores_com_bordas
from backend.grafo_viario import carregar_grafo_bh

import osmnx as ox


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def gerar_entregadores_fixo(N: int, bares_dict: dict, malha, seed: int = SEMENTE):
    """Gera N entregadores com semente fixa e retorna lista de dicts."""
    np.random.seed(seed)

    from backend.gerador_entregadores import gerar_entregadores
    lats, lons, origens = gerar_entregadores(N, bares=bares_dict)

    nos = ox.distance.nearest_nodes(malha, X=lons, Y=lats)

    entregadores = []
    for seq_id, (node_id, _) in enumerate(zip(nos, origens), start=1):
        dados = malha.nodes[node_id]
        lat_r = float(dados["y"])
        lon_r = float(dados["x"])
        entregadores.append({
            "id": seq_id,
            "lat": lat_r,
            "lon": lon_r,
            "geohash": encode(lat_r, lon_r, 8),
        })
    return entregadores


def buscar_so_celula_central(trie, lat: float, lon: float, raio_km: float,
                              precisao: int = None) -> list:
    """Busca apenas na célula central (sem células vizinhas) — para medir o ganho de borda."""
    if precisao is None:
        precisao = 6 if raio_km <= 1.2 else 5
    gh = encode(lat, lon, precisao)
    candidatos = {}
    for e in trie.searchNode(gh):
        candidatos[e["id"]] = e
    return [e for e in candidatos.values()
            if haversine(lat, lon, e["lat"], e["lon"]) <= raio_km]


def calcular_distancia_borda_normalizada(lat: float, lon: float, precisao: int = 6) -> float:
    """
    Retorna a distância normalizada à borda mais próxima da célula geohash
    (0 = centro exato, 1 = na borda da célula).
    """
    gh = encode(lat, lon, precisao)
    lat_c, lon_c, lat_err, lon_err = decode_geohash(gh)
    dist_lat = abs(lat - lat_c) / lat_err if lat_err > 0 else 0
    dist_lon = abs(lon - lon_c) / lon_err if lon_err > 0 else 0
    return max(dist_lat, dist_lon)


def encontrar_bar_por_bairro(bares: dict, termos: list) -> dict | None:
    """Retorna o primeiro bar cujo bairro contenha algum dos termos (case-insensitive)."""
    for bar in bares.values():
        bairro = bar.get("bairro", "").upper()
        for t in termos:
            if t.upper() in bairro:
                return bar
    return None


def encontrar_bar_proximo_borda(bares: dict, precisao: int = 6) -> dict:
    """Retorna o bar cujo lat/lon esteja mais próximo de uma fronteira de célula geohash."""
    melhor_bar, melhor_dist = None, -1.0
    for bar in bares.values():
        d = calcular_distancia_borda_normalizada(bar["lat"], bar["lon"], precisao)
        if d > melhor_dist:
            melhor_dist = d
            melhor_bar = bar
    return melhor_bar, melhor_dist


def encontrar_bar_mais_isolado(bares: dict, precisao: int = 6) -> dict:
    """
    Retorna o bar que possui menos vizinhos a 2 km — heurística para 'área pouco densa'.
    """
    lista = list(bares.values())
    min_vizinhos = float("inf")
    melhor_bar = lista[0]
    for bar in lista:
        vizinhos_count = sum(
            1 for outro in lista
            if outro["id"] != bar["id"]
            and haversine(bar["lat"], bar["lon"], outro["lat"], outro["lon"]) <= 2.0
        )
        if vizinhos_count < min_vizinhos:
            min_vizinhos = vizinhos_count
            melhor_bar = bar
    return melhor_bar


def medir_consulta(bar: dict, raio: float, entregadores: list,
                   incluir_sem_bordas: bool = False) -> dict:
    """
    Executa REPETICOES vezes a consulta e retorna métricas de tempo e contagens.
    """
    precisao = 6 if raio <= 1.2 else 5

    tempos_trie, tempos_busca = [], []
    resultados = None

    for _ in range(REPETICOES):
        t0 = time.perf_counter()
        trie = construir_trie(entregadores)
        t1 = time.perf_counter()
        resultados = buscar_entregadores_com_bordas(
            trie, bar["lat"], bar["lon"],
            raio_km=raio, haversine_func=haversine,
        )
        t2 = time.perf_counter()
        tempos_trie.append((t1 - t0) * 1000)
        tempos_busca.append((t2 - t1) * 1000)

    # Candidatos pré-filtro Haversine (apenas passaram pelo filtro geohash)
    trie_final = construir_trie(entregadores)
    gh = encode(bar["lat"], bar["lon"], precisao)
    celulas = vizinhos(gh)
    candidatos = {}
    for c in celulas:
        for e in trie_final.searchNode(c):
            candidatos[e["id"]] = e

    metricas = {
        "precisao": precisao,
        "celulas": len(celulas),
        "candidatos": len(candidatos),
        "resultados": len(resultados),
        "t_trie_media": round(float(np.mean(tempos_trie)), 2),
        "t_trie_dp": round(float(np.std(tempos_trie)), 2),
        "t_busca_media": round(float(np.mean(tempos_busca)), 2),
        "t_busca_dp": round(float(np.std(tempos_busca)), 2),
        "t_total": round(float(np.mean(tempos_trie)) + float(np.mean(tempos_busca)), 2),
    }

    if incluir_sem_bordas:
        sem = buscar_so_celula_central(trie_final, bar["lat"], bar["lon"], raio)
        metricas["resultados_central"] = len(sem)
        metricas["ganho_borda"] = len(resultados) - len(sem)

    return metricas


def imprimir_consulta(numero: int, descricao: str, bar: dict, raio: float,
                      N: int, m: dict, linhas: list):
    """Formata e exibe os resultados de uma consulta."""
    sep = "=" * 65
    linha = f"""
{sep}
  CONSULTA {numero}: {descricao}
{sep}
  Bar         : {bar['nome']}
  Bairro      : {bar.get('bairro', 'N/A')}
  Lat / Lon   : {bar['lat']:.6f}, {bar['lon']:.6f}
  Raio        : {raio} km
  N gerados   : {N}
  Precisão    : {m['precisao']}
  Células     : {m['celulas']}
  Candidatos  : {m['candidatos']}
  Resultados  : {m['resultados']}"""

    if "resultados_central" in m:
        linha += f"""
  Apenas célula central : {m['resultados_central']}
  Ganho c/ bordas       : {m['ganho_borda']}"""

    linha += f"""
  Trie (ms)   : {m['t_trie_media']:.2f} ± {m['t_trie_dp']:.2f}
  Busca (ms)  : {m['t_busca_media']:.2f} ± {m['t_busca_dp']:.2f}
  Total (ms)  : {m['t_total']:.2f}
"""
    print(linha)
    linhas.append(linha)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    linhas_saida = []

    cabecalho = """
================================================================
  EXPERIMENTOS - Trabalho Prático Algoritmos 2
  Semente numpy: {}   Repetições: {}
================================================================
""".format(SEMENTE, REPETICOES)
    print(cabecalho)
    linhas_saida.append(cabecalho)

    # ------------------------------------------------------------------
    # Carregamento de dados
    # ------------------------------------------------------------------
    print("[1/3] Carregando bares...")
    bares_dict = carregar_bares()
    print(f"      {len(bares_dict)} bares carregados.\n")

    print("[2/3] Carregando malha viária...")
    malha = carregar_grafo_bh()
    print("      Malha viária pronta.\n")

    print("[3/3] Gerando conjuntos de entregadores (N=200 e N=100)...")
    entregadores_200 = gerar_entregadores_fixo(200, bares_dict, malha, seed=SEMENTE)
    entregadores_100 = gerar_entregadores_fixo(100, bares_dict, malha, seed=SEMENTE)
    print(f"      {len(entregadores_200)} entregadores (N=200) prontos.")
    print(f"      {len(entregadores_100)} entregadores (N=100) prontos.\n")

    # ------------------------------------------------------------------
    # Seleção de bares para cada cenário
    # ------------------------------------------------------------------
    TERMOS_CENTRO = ["SAVASSI", "FUNCIONARIOS", "FUNCIONÁRIOS", "LOURDES",
                     "CENTRO", "BELVEDERE", "GUTIERREZ", "SANTO AGOSTINHO",
                     "CARMO", "ANCHIETA"]
    TERMOS_PERIFERIA = ["BARREIRO", "CARDOSO", "MILIONARIOS", "MILIONÁRIOS",
                        "JATOBA", "JATOBÁ", "MIRAMAR", "DIAMANTE",
                        "NORDESTE", "SAO CRISTOVAO"]

    bar_centro = encontrar_bar_por_bairro(bares_dict, TERMOS_CENTRO)
    bar_periferia = encontrar_bar_por_bairro(bares_dict, TERMOS_PERIFERIA)
    bar_borda, dist_borda = encontrar_bar_proximo_borda(bares_dict, precisao=6)
    bar_isolado = encontrar_bar_mais_isolado(bares_dict)

    # Fallback: se algum não for encontrado, usa o primeiro bar disponível
    lista_bares = list(bares_dict.values())
    if bar_centro is None:
        bar_centro = lista_bares[0]
    if bar_periferia is None:
        bar_periferia = lista_bares[len(lista_bares) // 2]
    if bar_borda is None:
        bar_borda = lista_bares[1]

    info_selecao = f"""Bares selecionados para os experimentos:
  Consulta 1 & 4 (centro)  : {bar_centro['nome']} [{bar_centro.get('bairro','?')}]
  Consulta 2 (periferia)   : {bar_periferia['nome']} [{bar_periferia.get('bairro','?')}]
  Consulta 3 (fronteira)   : {bar_borda['nome']} [{bar_borda.get('bairro','?')}]
                              dist. normaliz. à borda: {dist_borda:.4f}
  Consulta 5 (isolado)     : {bar_isolado['nome']} [{bar_isolado.get('bairro','?')}]
"""
    print(info_selecao)
    linhas_saida.append(info_selecao)

    resultados = []

    # ------------------------------------------------------------------
    # Consulta 1 – raio restrito em área densa (0,5 km, N=200)
    # ------------------------------------------------------------------
    m1 = medir_consulta(bar_centro, 0.5, entregadores_200)
    imprimir_consulta(1, "Raio restrito em área densa (0,5 km)",
                      bar_centro, 0.5, 200, m1, linhas_saida)
    resultados.append(("1 - Centro 0,5 km", bar_centro, 0.5, 200, m1))

    # ------------------------------------------------------------------
    # Consulta 2 – raio moderado em bairro periférico (2,0 km, N=200)
    # ------------------------------------------------------------------
    m2 = medir_consulta(bar_periferia, 2.0, entregadores_200)
    imprimir_consulta(2, "Raio moderado em bairro periférico (2,0 km)",
                      bar_periferia, 2.0, 200, m2, linhas_saida)
    resultados.append(("2 - Periferia 2,0 km", bar_periferia, 2.0, 200, m2))

    # ------------------------------------------------------------------
    # Consulta 3 – fronteira de célula (1,0 km, N=200)
    # ------------------------------------------------------------------
    m3 = medir_consulta(bar_borda, 1.0, entregadores_200, incluir_sem_bordas=True)
    imprimir_consulta(3, "Próxima à fronteira de célula (1,0 km)",
                      bar_borda, 1.0, 200, m3, linhas_saida)
    resultados.append(("3 - Fronteira 1,0 km", bar_borda, 1.0, 200, m3))

    # ------------------------------------------------------------------
    # Consulta 4 – raio amplo (5,0 km, N=200)
    # ------------------------------------------------------------------
    m4 = medir_consulta(bar_centro, 5.0, entregadores_200)
    imprimir_consulta(4, "Raio amplo (5,0 km, precisão 5)",
                      bar_centro, 5.0, 200, m4, linhas_saida)
    resultados.append(("4 - Centro 5,0 km", bar_centro, 5.0, 200, m4))

    # ------------------------------------------------------------------
    # Consulta 5 – raio muito pequeno, resultado esperado zero (0,1 km, N=100)
    # ------------------------------------------------------------------
    m5 = medir_consulta(bar_isolado, 0.1, entregadores_100)
    imprimir_consulta(5, "Raio muito pequeno — resultado vazio esperado (0,1 km)",
                      bar_isolado, 0.1, 100, m5, linhas_saida)
    resultados.append(("5 - Isolado 0,1 km", bar_isolado, 0.1, 100, m5))

    # ------------------------------------------------------------------
    # Tabela consolidada
    # ------------------------------------------------------------------
    tabela = """
================================================================
  TABELA 2 — RESUMO DOS EXPERIMENTOS
================================================================
 #  Região/Bar          Raio  P  Células  Cand.  Result.  Total(ms)
----------------------------------------------------------------"""
    print(tabela)
    linhas_saida.append(tabela)

    for i, (desc, bar, raio, N, m) in enumerate(resultados, start=1):
        linha_tab = (
            f" {i}  {bar['nome'][:20]:<20s}  "
            f"{raio:4.1f}  {m['precisao']}  "
            f"{m['celulas']:7d}  {m['candidatos']:5d}  "
            f"{m['resultados']:7d}  {m['t_total']:9.2f}"
        )
        print(linha_tab)
        linhas_saida.append(linha_tab)

    rodape = "\n================================================================\n"
    print(rodape)
    linhas_saida.append(rodape)

    # ------------------------------------------------------------------
    # Experimento extra: Trie vs N (para o gráfico de linearidade)
    # ------------------------------------------------------------------
    print("\nExperimento de escalabilidade: tempo de construção da Trie vs N\n")
    linhas_saida.append("\nExperimento de escalabilidade: tempo de construção da Trie vs N\n")
    bar_ref = bar_centro

    escalabilidade = []
    for n_val in list(range(10, 961, 50)) + [1000]:
        np.random.seed(SEMENTE)
        ents = gerar_entregadores_fixo(n_val, bares_dict, malha, seed=SEMENTE)
        t_med = []
        for _ in range(REPETICOES):
            t0 = time.perf_counter()
            construir_trie(ents)
            t1 = time.perf_counter()
            t_med.append((t1 - t0) * 1000)
        ms = round(float(np.mean(t_med)), 3)
        escalabilidade.append((n_val, ms))
        linha_esc = f"  N={n_val:4d}  Trie={ms:.3f} ms"
        print(linha_esc)
        linhas_saida.append(linha_esc)

    # ------------------------------------------------------------------
    # Experimento de variação de raio vs resultados e runtime
    # ------------------------------------------------------------------
    RAIOS_TESTE = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0,
                   7.0, 10.0, 15.0, 20.0, 25.0, 30.0]

    cab_raio = """
================================================================
  EXPERIMENTO: Raio vs Resultados / Runtime  (N=200, bar central)
================================================================
  Raio(km)  Precisão  Células  Candidatos  Resultados  Total(ms)
----------------------------------------------------------------"""
    print(cab_raio)
    linhas_saida.append(cab_raio)

    trie_raio = construir_trie(entregadores_200)

    for raio_val in RAIOS_TESTE:
        precisao_r = 6 if raio_val <= 1.2 else 5
        t_list = []
        res_count = 0
        for _ in range(REPETICOES):
            t0 = time.perf_counter()
            encontrados_r = buscar_entregadores_com_bordas(
                trie_raio, bar_centro["lat"], bar_centro["lon"],
                raio_km=raio_val, haversine_func=haversine,
            )
            t1 = time.perf_counter()
            t_list.append((t1 - t0) * 1000)
            res_count = len(encontrados_r)

        gh_r = encode(bar_centro["lat"], bar_centro["lon"], precisao_r)
        cells_r = vizinhos(gh_r)
        cands_r = {}
        for c in cells_r:
            for e in trie_raio.searchNode(c):
                cands_r[e["id"]] = e

        ms_r = round(float(np.mean(t_list)), 3)
        linha_r = (
            f"  {raio_val:7.1f}   {precisao_r:7d}  {len(cells_r):7d}  "
            f"{len(cands_r):10d}  {res_count:10d}  {ms_r:9.3f}"
        )
        print(linha_r)
        linhas_saida.append(linha_r)

    linhas_saida.append("\n================================================================\n")
    print()

    # ------------------------------------------------------------------
    # Salvar resultado em arquivo
    # ------------------------------------------------------------------
    os.makedirs("data/output", exist_ok=True)
    caminho = "data/output/experimentos.txt"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_saida))

    print(f"\nResultados salvos em: {caminho}")


if __name__ == "__main__":
    main()
