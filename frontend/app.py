import os
from backend.bairros import BairrosOficiaisBH
from backend.bares import carregar_bares
from backend.geohash import encode, haversine
from backend.gerador_entregadores import armazenar_dados_entregadores
from backend.grafo_viario import carregar_grafo_bh
from backend.rotas import calcular_rota_viaria
from backend.trie import TrieTextualBares
from backend.trie_and_geohash import (
    buscar_entregadores_com_bordas,
    construir_trie,
)
import dash
from dash import Input, Output, State, dash_table, dcc, html
from frontend.mapa import criar_mapa

# Carregamento inicial de bases oficiais
BARES_DICT = carregar_bares()
BARES = list(BARES_DICT.values()) if isinstance(BARES_DICT, dict) else BARES_DICT
BUSCADOR_BARES = TrieTextualBares(BARES)
bairros_bh = BairrosOficiaisBH("data/input/BAIRRO_OFICIAL.shp")
MALHA = carregar_grafo_bh()

# -------------------------------------------------------
# App Dash Layout
# -------------------------------------------------------
app = dash.Dash(__name__)
app.title = "UFOOD - BH"

app.layout = html.Div(
    [
        html.H2(
            "UFOOD - BH — Busca de Entregadores",
            style={"textAlign": "center", "margin": "16px 0"},
        ),
        html.Div(
            [
                # Painel esquerdo (Controles)
                html.Div(
                    [
                        html.Label("Quantidade de entregadores:"),
                        dcc.Input(
                            id="inp-qtd",
                            type="number",
                            value=100,
                            min=10,
                            max=500,
                            step=10,
                            style={"width": "100%", "marginBottom": "8px"},
                        ),
                        html.Button(
                            "Gerar Entregadores",
                            id="btn-gerar",
                            n_clicks=0,
                            style={
                                "width": "100%",
                                "padding": "8px",
                                "marginBottom": "16px",
                            },
                        ),
                        html.Hr(),
                        # BARRA ÚNICA DE BUSCA E SELEÇÃO
                        html.Label("Buscar Bar (Nome, Rua ou Bairro):"),
                        dcc.Dropdown(
                            id="dd-bar",
                            placeholder="Digite para pesquisar em tempo real...",
                            clearable=False,
                            searchable=True,
                            options=BUSCADOR_BARES.obter_opcoes_iniciais(40),
                            style={"marginBottom": "16px"},
                        ),
                        html.Hr(),
                        html.Label("Raio de busca (km):"),
                        dcc.Input(
                            id="inp-raio",
                            type="number",
                            value=2.0,
                            min=0.1,
                            max=30.0,
                            step=0.1,
                            style={"width": "100%", "marginBottom": "8px"},
                        ),
                        html.Button(
                            "Buscar Entregadores",
                            id="btn-buscar",
                            n_clicks=0,
                            style={
                                "width": "100%",
                                "padding": "8px",
                                "backgroundColor": "#4CAF50",
                                "color": "white",
                                "border": "none",
                                "cursor": "pointer",
                                "marginBottom": "16px",
                            },
                        ),
                        html.Hr(),
                        html.Div(
                            id="status",
                            children="Sistema pronto.",
                            style={"fontSize": "13px", "color": "#555"},
                        ),
                    ],
                    style={
                        "width": "280px",
                        "padding": "16px",
                        "border": "1px solid #ddd",
                        "borderRadius": "6px",
                        "background": "#f9f9f9",
                        "marginRight": "12px",
                        "flexShrink": "0",
                    },
                ),
                # Mapa (Visualização)
                html.Div(
                    [
                        dcc.Graph(
                            id="mapa", figure=criar_mapa([], None, set())
                        ),
                    ],
                    style={"flex": "1"},
                ),
            ],
            style={"display": "flex", "padding": "0 16px"},
        ),
        # Tabela de resultados
        html.Div(
            [
                html.H4("Resultados", style={"margin": "16px 0 8px"}),
                dash_table.DataTable(
                    id="tabela",
                    columns=[
                        {"name": "ID", "id": "id"},
                        {"name": "Bairro Oficial", "id": "bairro"},
                        {"name": "Distância (km)", "id": "dist"},
                        {"name": "Tempo estimado", "id": "tempo"},
                        {"name": "Geohash", "id": "gh"},
                    ],
                    data=[],
                    style_cell={"textAlign": "center", "padding": "6px"},
                    style_header={
                        "fontWeight": "bold",
                        "backgroundColor": "#eee",
                    },
                    page_size=10,
                ),
            ],
            style={"padding": "0 16px 24px"},
        ),
        dcc.Store(id="store-entregadores", data=[]),
        dcc.Store(id="store-bar", data=None),
    ]
)

# -------------------------------------------------------
# Callbacks do Dash
# -------------------------------------------------------


@app.callback(
    Output("dd-bar", "options"),
    Input("dd-bar", "search_value"),
)
def atualizar_opcoes_dropdown(termo_pesquisa):
    if not termo_pesquisa:
        return dash.no_update
    return BUSCADOR_BARES.buscar(termo_pesquisa, limite=60)


@app.callback(
    Output("store-bar", "data"),
    Output("mapa", "figure", allow_duplicate=True),
    Input("dd-bar", "value"),
    State("store-entregadores", "data"),
    State("inp-raio", "value"),
    prevent_initial_call=True,
)
def salvar_bar(idx, entregadores, raio):
    if idx is None:
        return None, dash.no_update
    bar = BARES[idx]
    raio = float(raio or 2.0)
    fig = criar_mapa(entregadores, bar, set(), raio_km=raio)
    return bar, fig


@app.callback(
    Output("store-entregadores", "data"),
    Output("mapa", "figure"),
    Output("status", "children"),
    Input("btn-gerar", "n_clicks"),
    State("inp-qtd", "value"),
    State("store-bar", "data"),
    prevent_initial_call=True,
)
def cb_gerar(n_clicks, quantidade, bar):
    quantidade = int(quantidade or 100)
    entregadores_gerados = armazenar_dados_entregadores(
        N=quantidade, bares=BARES_DICT
    )
    fig = criar_mapa(entregadores_gerados, bar, set())
    return (
        entregadores_gerados,
        fig,
        f"{len(entregadores_gerados)} entregadores gerados e corrigidos via backend.",
    )


@app.callback(
    Output("mapa", "figure", allow_duplicate=True),
    Output("tabela", "data"),
    Output("status", "children", allow_duplicate=True),
    Input("btn-buscar", "n_clicks"),
    State("store-bar", "data"),
    State("inp-raio", "value"),
    State("store-entregadores", "data"),
    prevent_initial_call=True,
)
def cb_buscar(n_clicks, bar, raio, entregadores):
    if not entregadores:
        return dash.no_update, [], "Gere os entregadores primeiro."
    if not bar:
        return dash.no_update, [], "Selecione um bar."

    raio = float(raio or 2.0)

    trie = construir_trie(entregadores)
    encontrados = buscar_entregadores_com_bordas(
        trie,
        bar["lat"],
        bar["lon"],
        raio_km=raio,
        haversine_func=haversine,
    )

    ids_encontrados = {e["id"] for e in encontrados}

    encontrados_ordenados = sorted(
        encontrados,
        key=lambda e: haversine(bar["lat"], bar["lon"], e["lat"], e["lon"]),
    )

    rota_coords = None
    id_mais_proximo = None
    dist_rota_km = 0.0

    if encontrados_ordenados:
        mais_proximo = encontrados_ordenados[0]
        id_mais_proximo = mais_proximo["id"]

        r_lats, r_lons, dist_metros = calcular_rota_viaria(
            MALHA,
            lat_origem=mais_proximo["lat"],
            lon_origem=mais_proximo["lon"],
            lat_destino=bar["lat"],
            lon_destino=bar["lon"],
        )
        rota_coords = (r_lats, r_lons)
        dist_rota_km = dist_metros / 1000.0

    fig = criar_mapa(
        entregadores,
        bar,
        ids_encontrados,
        raio_km=raio,
        rota_coords=rota_coords,
        id_mais_proximo=id_mais_proximo,
    )

    linhas = []
    for e in encontrados_ordenados:
        dist = haversine(bar["lat"], bar["lon"], e["lat"], e["lon"])
        tempo = (dist / 30.0) * 60
        bairro_nome = bairros_bh.identificar_bairro(e["lat"], e["lon"])

        linhas.append({
            "id": (
                f"★ {e['id']} (Mais Próximo)" if e["id"] == id_mais_proximo else e["id"]
            ),
            "bairro": bairro_nome,
            "dist": f"{dist:.2f}",
            "tempo": f"{tempo:.0f} min",
            "gh": e.get("geohash", encode(e["lat"], e["lon"], 8)),
        })

    msg = (
        f"Bar: {bar['nome']} | Encontrados: {len(encontrados)} | "
        + (
            f"Distância real da rota (ruas): {dist_rota_km:.2f} km"
            if id_mais_proximo
            else "Nenhum entregador no raio."
        )
    )

    return fig, linhas, msg


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="127.0.0.1", port=porta)