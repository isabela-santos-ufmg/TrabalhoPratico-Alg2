import os
import math
import random
import threading
import pickle
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go

try:
    import osmnx as ox
    OSMNX_OK = True
except ImportError:
    OSMNX_OK = False

from geohash import encode

# -------------------------------------------------------
# Trie compacta (Patricia Trie)
# -------------------------------------------------------
class Node:
    def __init__(self, rotulo=""):
        self.rotulo = rotulo
        self.filhos = {}
        self.valores = []

class Trie:
    def __init__(self):
        self.root = Node(rotulo="")
        self.total_nos = 1

    def longest_prefix(self, s1, s2):
        comum = 0
        limite = min(len(s1), len(s2))
        for i in range(limite):
            if s1[i] != s2[i]:
                break
            comum += 1
        return comum

    def addNode(self, node, entregador):
        atual = self.root
        restante = node

        while restante:
            begin = restante[0]
            filho = atual.filhos.get(begin)

            if filho is None:
                novo_node = Node(rotulo=restante)
                novo_node.valores.append(entregador)
                atual.filhos[begin] = novo_node
                self.total_nos += 1
                return

            l = self.longest_prefix(restante, filho.rotulo)

            if l == len(filho.rotulo):
                restante = restante[l:]
                atual = filho
                if restante == "":
                    filho.valores.append(entregador)
                    return
            else:
                novo_node = Node(rotulo=filho.rotulo[:l])
                filho.rotulo = filho.rotulo[l:]
                novo_node.filhos[filho.rotulo[0]] = filho

                folha = Node(rotulo=restante[l:])
                folha.valores.append(entregador)
                novo_node.filhos[folha.rotulo[0]] = folha  # corrigido: era folha.rotulo[l:]

                atual.filhos[begin] = novo_node
                self.total_nos += 2
                return

    def searchNode(self, node):
        if not node:
            return []
        atual = self.root
        restante = node
        while True:
            filho_match = atual.filhos.get(restante[0])
            if not filho_match:
                return []
            l = self.longest_prefix(restante, filho_match.rotulo)
            if l == len(filho_match.rotulo):
                restante = restante[l:]
                atual = filho_match
                if restante == "":
                    return atual.valores
            else:
                return []

    def coletar(self, node):
        resultado = []
        pilha = [node]
        while pilha:
            n = pilha.pop()
            resultado.extend(n.valores)
            pilha.extend(n.filhos.values())
        return resultado

# -------------------------------------------------------
# Haversine + busca com tratamento de bordas
# -------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

def decode_geohash(geohash):
    BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    i = 0
    for char in geohash:
        indice = BASE32.index(char)
        for pos in range(4, -1, -1):
            bit = (indice >> pos) & 1
            if i % 2 == 0:
                meio = (lon_min + lon_max) / 2
                if bit:
                    lon_min = meio
                else:
                    lon_max = meio
            else:
                meio = (lat_min + lat_max) / 2
                if bit:
                    lat_min = meio
                else:
                    lat_max = meio
            i += 1
    lat_c = (lat_min + lat_max) / 2
    lon_c = (lon_min + lon_max) / 2
    lat_err = (lat_max - lat_min) / 2
    lon_err = (lon_max - lon_min) / 2
    return lat_c, lon_c, lat_err, lon_err

def vizinhos(geohash):
    precisao = len(geohash)
    lat_c, lon_c, lat_err, lon_err = decode_geohash(geohash)
    passo_lat = lat_err * 2.1
    passo_lon = lon_err * 2.1
    direcoes = [
        ( passo_lat,       0),
        (-passo_lat,       0),
        (       0,  passo_lon),
        (       0, -passo_lon),
        ( passo_lat,  passo_lon),
        ( passo_lat, -passo_lon),
        (-passo_lat,  passo_lon),
        (-passo_lat, -passo_lon),
    ]
    celulas = {geohash}
    for dlat, dlon in direcoes:
        nova_lat = max(-90.0, min(90.0, lat_c + dlat))
        nova_lon = max(-180.0, min(180.0, lon_c + dlon))
        celulas.add(encode(nova_lat, nova_lon, precisao))
    return list(celulas)

def buscar_por_prefixo(trie, prefixo):
    if not prefixo:
        return trie.coletar(trie.root)
    atual = trie.root
    restante = prefixo
    while restante:
        filho = atual.filhos.get(restante[0])
        if filho is None:
            return []
        l = trie.longest_prefix(restante, filho.rotulo)
        if l == len(restante):
            return trie.coletar(filho)
        elif l == len(filho.rotulo):
            restante = restante[l:]
            atual = filho
        else:
            return []
    return trie.coletar(atual)

def buscar_entregadores(trie, lat, lon, raio_km, precisao=6):
    gh = encode(lat, lon, precisao)
    celulas = vizinhos(gh)
    candidatos = {}
    for celula in celulas:
        for entregador in buscar_por_prefixo(trie, celula):
            candidatos[entregador["id"]] = entregador
    resultado = []
    for entregador in candidatos.values():
        distancia = haversine(lat, lon, entregador["lat"], entregador["lon"])
        if distancia <= raio_km:
            resultado.append(entregador)
    return resultado

# -------------------------------------------------------
# Carrega restaurantes do Excel (ou usa fallback)
# -------------------------------------------------------
EXCEL_PATH = "bares_com_geohash.xlsx"

RESTAURANTES_FALLBACK = [
    {"nome": "Savassi",        "lat": -19.9337, "lon": -43.9328},
    {"nome": "Lourdes",        "lat": -19.9275, "lon": -43.9482},
    {"nome": "Centro",         "lat": -19.9187, "lon": -43.9381},
    {"nome": "Pampulha",       "lat": -19.8660, "lon": -43.9687},
    {"nome": "Santa Efigênia", "lat": -19.9230, "lon": -43.9190},
    {"nome": "Floresta",       "lat": -19.9126, "lon": -43.9294},
    {"nome": "Boa Viagem",     "lat": -19.9469, "lon": -43.9334},
    {"nome": "Mangabeiras",    "lat": -19.9484, "lon": -43.9408},
    {"nome": "Funcionários",   "lat": -19.9295, "lon": -43.9381},
    {"nome": "Santa Teresa",   "lat": -19.9138, "lon": -43.8928},
]

def carregar_restaurantes():
    if not os.path.exists(EXCEL_PATH):
        print("Excel não encontrado, usando restaurantes de exemplo")
        return RESTAURANTES_FALLBACK

    df = pd.read_excel(EXCEL_PATH)
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

    restaurantes = []
    for _, linha in df.iterrows():
        nome = str(linha.get("ENDERECO_CONSULTADO", "")).strip()
        if nome == "":
            nome = "Restaurante"
        restaurantes.append({
            "nome": nome,
            "lat": float(linha["LATITUDE"]),
            "lon": float(linha["LONGITUDE"]),
        })

    print(f"Carregados {len(restaurantes)} restaurantes do Excel")
    return restaurantes

RESTAURANTES = carregar_restaurantes()

# -------------------------------------------------------
# Grafo da malha viária (osmnx) — com cache em disco
# -------------------------------------------------------
GRAFO_CACHE = "grafo_bh.pkl"

grafo_bh = None
grafo_pronto = False


def carregar_grafo():
    global grafo_bh, grafo_pronto
    if not OSMNX_OK:
        grafo_pronto = True
        return

    if os.path.exists(GRAFO_CACHE):
        print("Carregando grafo do cache local...")
        with open(GRAFO_CACHE, "rb") as f:
            grafo_bh = pickle.load(f)
        print("Grafo carregado do cache!")
    else:
        print("Baixando malha viária de BH (primeira vez, pode demorar)...")
        grafo_bh = ox.graph_from_place("Belo Horizonte, Brasil", network_type="drive")
        with open(GRAFO_CACHE, "wb") as f:
            pickle.dump(grafo_bh, f)
        print("Grafo salvo em cache para as próximas execuções!")

    grafo_pronto = True


# inicia carregamento em background assim que o app sobe
threading.Thread(target=carregar_grafo, daemon=True).start()

def snap_para_rua(lat, lon):
    # versão escalar — usada apenas como fallback
    if grafo_bh is None:
        return lat, lon
    no = ox.nearest_nodes(grafo_bh, lon, lat)
    return grafo_bh.nodes[no]["y"], grafo_bh.nodes[no]["x"]

# -------------------------------------------------------
# Geração de entregadores com distribuição normal
# -------------------------------------------------------
SIGMA = 0.008  # desvio padrão em graus (~0.8 km)

def gerar_entregadores(quantidade):
    # sorteia centros aleatórios dentre os restaurantes
    indices = [random.randint(0, len(RESTAURANTES) - 1) for _ in range(quantidade)]

    lats = np.array([RESTAURANTES[i]["lat"] for i in indices])
    lons = np.array([RESTAURANTES[i]["lon"] for i in indices])

    # adiciona ruído gaussiano centrado no restaurante
    lats += np.random.normal(0, SIGMA, quantidade)
    lons += np.random.normal(0, SIGMA, quantidade)

    # limita dentro de BH
    lats = np.clip(lats, -20.10, -19.75)
    lons = np.clip(lons, -44.10, -43.85)

    # projeta todos os pontos para a via mais próxima de uma vez (vetorizado)
    if OSMNX_OK and grafo_bh is not None:
        nos = ox.nearest_nodes(grafo_bh, lons.tolist(), lats.tolist())
        entregadores = [
            {"id": i + 1, "lat": grafo_bh.nodes[no]["y"], "lon": grafo_bh.nodes[no]["x"]}
            for i, no in enumerate(nos)
        ]
    else:
        entregadores = [
            {"id": i + 1, "lat": float(lats[i]), "lon": float(lons[i])}
            for i in range(quantidade)
        ]

    return entregadores

# -------------------------------------------------------
# Trie
# -------------------------------------------------------
def construir_trie(entregadores):
    t = Trie()
    for e in entregadores:
        gh = encode(e["lat"], e["lon"], 8)
        t.addNode(gh, e)
    return t

# -------------------------------------------------------
# Círculo de raio no mapa
# -------------------------------------------------------
def pontos_circulo(lat_c, lon_c, raio_km, n=60):
    lats = []
    lons = []
    for i in range(n + 1):
        angulo = math.radians(i * 360 / n)
        dlat = raio_km / 111.32
        dlon = raio_km / (111.32 * math.cos(math.radians(lat_c)))
        lats.append(lat_c + dlat * math.sin(angulo))
        lons.append(lon_c + dlon * math.cos(angulo))
    return lats, lons

# -------------------------------------------------------
# Mapa
# -------------------------------------------------------
def criar_mapa(entregadores, restaurante, ids_encontrados, raio_km=None):
    fig = go.Figure()

    # trace vazio garante que o mapa sempre renderiza
    fig.add_trace(go.Scattermap(lat=[], lon=[], mode="markers", showlegend=False))

    # entregadores fora do raio (moto cinza)
    fora = [e for e in entregadores if e["id"] not in ids_encontrados]
    if fora:
        fig.add_trace(go.Scattermap(
            lat=[e["lat"] for e in fora],
            lon=[e["lon"] for e in fora],
            mode="text",
            text=["🏍"] * len(fora),
            textfont=dict(size=14, color="#777777"),
            hovertext=[f"Entregador {e['id']}" for e in fora],
            hoverinfo="text",
            name="Entregadores",
        ))

    # entregadores dentro do raio (moto verde)
    dentro = [e for e in entregadores if e["id"] in ids_encontrados]
    if dentro:
        fig.add_trace(go.Scattermap(
            lat=[e["lat"] for e in dentro],
            lon=[e["lon"] for e in dentro],
            mode="text",
            text=["🏍"] * len(dentro),
            textfont=dict(size=20, color="#00AA00"),
            hovertext=[f"Entregador {e['id']} ✓" for e in dentro],
            hoverinfo="text",
            name="Dentro do raio",
        ))

    # círculo mostrando o raio de busca
    if restaurante and raio_km:
        lats_c, lons_c = pontos_circulo(restaurante["lat"], restaurante["lon"], raio_km)
        fig.add_trace(go.Scattermap(
            lat=lats_c,
            lon=lons_c,
            mode="lines",
            line=dict(color="rgba(25, 118, 210, 0.7)", width=2),
            showlegend=False,
            hoverinfo="skip",
        ))

    # restaurante (estrela vermelha)
    if restaurante:
        fig.add_trace(go.Scattermap(
            lat=[restaurante["lat"]],
            lon=[restaurante["lon"]],
            mode="markers+text",
            marker=dict(size=22, color="#E53935", symbol="star"),
            text=[restaurante["nome"][:30]],
            textposition="top right",
            textfont=dict(size=12, color="#E53935"),
            hoverinfo="text",
            name="Restaurante",
        ))

    fig.update_layout(
        map_style="open-street-map",
        map_center={"lat": -19.92, "lon": -43.95},
        map_zoom=11,
        height=540,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend=dict(orientation="h", y=0),
        uirevision="mapa",
    )
    return fig

# -------------------------------------------------------
# App Dash
# -------------------------------------------------------
app = dash.Dash(__name__)
app.title = "EntregaBH"

app.layout = html.Div([
    html.H2("EntregaBH — Busca de Entregadores",
            style={"textAlign": "center", "margin": "16px 0"}),

    html.Div([

        # Painel esquerdo
        html.Div([

            html.Label("Quantidade de entregadores:"),
            dcc.Input(id="inp-qtd", type="number", value=100,
                      min=10, max=500, step=10,
                      style={"width": "100%", "marginBottom": "8px"}),

            html.Button("Gerar Entregadores", id="btn-gerar", n_clicks=0,
                        style={"width": "100%", "padding": "8px",
                               "marginBottom": "16px"}),

            html.Hr(),

            html.Label("Buscar restaurante:"),
            dcc.Input(id="inp-busca", type="text",
                      placeholder="Digite o nome ou endereço...",
                      debounce=True,
                      style={"width": "100%", "marginBottom": "8px"}),

            dcc.Dropdown(id="dd-rest",
                         placeholder="Selecione um restaurante...",
                         clearable=False,
                         style={"marginBottom": "16px"}),

            html.Hr(),

            html.Label("Raio de busca (km):"),
            dcc.Input(id="inp-raio", type="number", value=2.0,
                      min=0.1, max=30.0, step=0.1,
                      style={"width": "100%", "marginBottom": "8px"}),

            html.Button("Buscar Entregadores", id="btn-buscar", n_clicks=0,
                        style={"width": "100%", "padding": "8px",
                               "backgroundColor": "#4CAF50", "color": "white",
                               "border": "none", "cursor": "pointer",
                               "marginBottom": "16px"}),

            html.Hr(),
            html.Div(id="status", style={"fontSize": "13px", "color": "#555"}),

        ], style={"width": "240px", "padding": "16px",
                  "border": "1px solid #ddd", "borderRadius": "6px",
                  "background": "#f9f9f9", "marginRight": "12px",
                  "flexShrink": "0"}),

        # Mapa
        html.Div([
            dcc.Graph(id="mapa", figure=criar_mapa([], None, set())),
        ], style={"flex": "1"}),

    ], style={"display": "flex", "padding": "0 16px"}),

    # Tabela de resultados
    html.Div([
        html.H4("Resultados", style={"margin": "16px 0 8px"}),
        dash_table.DataTable(
            id="tabela",
            columns=[
                {"name": "ID",             "id": "id"},
                {"name": "Distância (km)", "id": "dist"},
                {"name": "Tempo estimado", "id": "tempo"},
                {"name": "Geohash",        "id": "gh"},
            ],
            data=[],
            style_cell={"textAlign": "center", "padding": "6px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#eee"},
            page_size=10,
        ),
    ], style={"padding": "0 16px 24px"}),

    dcc.Store(id="store-entregadores", data=[]),
    dcc.Store(id="store-rest", data=None),
    dcc.Interval(id="iv-status", interval=2000, n_intervals=0),
])

# -------------------------------------------------------
# Callbacks
# -------------------------------------------------------

@app.callback(
    Output("status", "children", allow_duplicate=True),
    Output("iv-status", "disabled"),
    Input("iv-status", "n_intervals"),
    prevent_initial_call=True,
)
def cb_status_grafo(_):
    if not OSMNX_OK:
        return "osmnx não instalado — sem snapping viário", True
    if grafo_pronto and grafo_bh is not None:
        return "✓ Malha viária pronta — pode gerar entregadores", True
    if grafo_pronto and grafo_bh is None:
        return "⚠ Falha ao carregar malha viária", True
    return "⏳ Carregando malha viária de BH...", False


@app.callback(
    Output("dd-rest", "options"),
    Input("inp-busca", "value"),
)
def atualizar_opcoes(termo):
    if not termo or len(termo.strip()) < 2:
        # mostra os primeiros 20 como sugestão
        opcoes = []
        for i in range(min(20, len(RESTAURANTES))):
            opcoes.append({"label": RESTAURANTES[i]["nome"][:60], "value": i})
        return opcoes

    termo = termo.strip().lower()
    opcoes = []
    for i, r in enumerate(RESTAURANTES):
        if termo in r["nome"].lower():
            opcoes.append({"label": r["nome"][:60], "value": i})
        if len(opcoes) == 20:
            break
    return opcoes


@app.callback(
    Output("store-rest", "data"),
    Input("dd-rest", "value"),
)
def salvar_restaurante(idx):
    if idx is None:
        return None
    return RESTAURANTES[idx]


@app.callback(
    Output("store-entregadores", "data"),
    Output("mapa", "figure"),
    Output("status", "children"),
    Input("btn-gerar", "n_clicks"),
    State("inp-qtd", "value"),
    State("store-rest", "data"),
    prevent_initial_call=True,
)
def cb_gerar(n_clicks, quantidade, restaurante):
    if not grafo_pronto:
        return dash.no_update, dash.no_update, "⏳ Malha viária ainda carregando, aguarde..."

    quantidade = quantidade or 100
    entregadores = gerar_entregadores(int(quantidade))
    fig = criar_mapa(entregadores, restaurante, set())

    msg = f"{len(entregadores)} entregadores gerados."
    if not OSMNX_OK:
        msg += " (instale osmnx para snapping viário)"

    return entregadores, fig, msg


@app.callback(
    Output("mapa", "figure", allow_duplicate=True),
    Output("tabela", "data"),
    Output("status", "children", allow_duplicate=True),
    Input("btn-buscar", "n_clicks"),
    State("store-rest", "data"),
    State("inp-raio", "value"),
    State("store-entregadores", "data"),
    prevent_initial_call=True,
)
def cb_buscar(n_clicks, restaurante, raio, entregadores):
    if not entregadores:
        return dash.no_update, [], "Gere os entregadores primeiro."
    if not restaurante:
        return dash.no_update, [], "Selecione um restaurante."

    raio = float(raio or 2.0)

    trie = construir_trie(entregadores)
    encontrados = buscar_entregadores(
        trie, restaurante["lat"], restaurante["lon"],
        raio_km=raio, precisao=6
    )

    ids_encontrados = set()
    for e in encontrados:
        ids_encontrados.add(e["id"])

    fig = criar_mapa(entregadores, restaurante, ids_encontrados, raio_km=raio)

    # monta tabela ordenada por distância
    linhas = []
    encontrados_ordenados = sorted(
        encontrados,
        key=lambda e: haversine(restaurante["lat"], restaurante["lon"], e["lat"], e["lon"])
    )
    for e in encontrados_ordenados:
        dist = haversine(restaurante["lat"], restaurante["lon"], e["lat"], e["lon"])
        tempo = dist / 30 * 60  # tempo em minutos (30 km/h)
        linhas.append({
            "id":    e["id"],
            "dist":  f"{dist:.2f}",
            "tempo": f"{tempo:.0f} min",
            "gh":    encode(e["lat"], e["lon"], 6),
        })

    msg = (f"Restaurante: {restaurante['nome'][:40]} | "
           f"Raio: {raio} km | "
           f"Encontrados: {len(encontrados)} de {len(entregadores)}")

    return fig, linhas, msg


if __name__ == "__main__":
    app.run(debug=False)
