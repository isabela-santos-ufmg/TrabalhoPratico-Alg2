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

BARES_DICT = carregar_bares()
BARES = list(BARES_DICT.values()) if isinstance(BARES_DICT, dict) else BARES_DICT
BUSCADOR_BARES = TrieTextualBares(BARES)
bairros_bh = BairrosOficiaisBH("data/input/BAIRRO_OFICIAL.shp")
MALHA = carregar_grafo_bh()

app = dash.Dash(__name__)
app.title = "UFOOD - BH | Central de Entregadores"

app.layout = html.Div(
    className="app-container",
    children=[
        html.Div(
            className="header-container",
            children=[
                html.Div(
                    className="header-nav",
                    children=[
                        html.Div(
                            children=[html.Span("🛵 Ufood", className="logo-text")]
                        ),
                        html.Div(
                            className="nav-links",
                            children=[
                                html.Span("Entregadores", className="nav-link-active"),
                                html.Span("Como funciona", className="nav-link"),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="header-user",
                    children=[
                        html.Span("📍 Belo Horizonte, MG", style={"fontWeight": "500"}),
                        html.Div(className="user-badge", children="U"),
                    ],
                ),
            ],
        ),
        html.Div(
            className="main-content",
            children=[
                html.Div(
                    className="section-header",
                    children=[
                        html.Div(
                            children=[
                                html.H1("Central de entregadores", className="section-title"),
                                html.P(
                                    "Gere entregadores e encontre quem está perto do seu endereço.",
                                    className="section-subtitle",
                                ),
                            ]
                        ),
                        html.Div(
                            className="live-badge",
                            children="🔴 Visualização em tempo real do mapa",
                        ),
                    ],
                ),
                html.Div(
                    className="grid-container",
                    children=[
                        html.Div(
                            className="sidebar-panel",
                            children=[
                                # PASSO 1: ENTREGADORES
                                html.Div(
                                    children=[
                                        html.Div(
                                            className="step-header",
                                            children=[
                                                html.Span("1", className="step-number"),
                                                html.Span(
                                                    "Comece pelos entregadores",
                                                    className="step-title",
                                                ),
                                            ],
                                        ),
                                        html.P(
                                            "Quantidade para distribuir na malha viária:",
                                            className="input-label",
                                        ),
                                        dcc.Input(
                                            id="inp-qtd",
                                            type="number",
                                            value=150,
                                            min=1,
                                            step=1,
                                            className="custom-input",
                                        ),
                                        dcc.Loading(
                                            id="loading-gerar",
                                            type="dot",
                                            color="#EA1D2C",
                                            children=[
                                                html.Button(
                                                    "🔀 Gerar Entregadores",
                                                    id="btn-gerar",
                                                    n_clicks=0,
                                                    className="btn-primary",
                                                )
                                            ],
                                        ),
                                    ]
                                ),
                                html.Hr(className="divider"),
                                # PASSO 2: RESTAURANTE (Único)
                                html.Div(
                                    children=[
                                        html.Div(
                                            className="step-header",
                                            children=[
                                                html.Span("2", className="step-number"),
                                                html.Span(
                                                    "Encontre o restaurante",
                                                    className="step-title",
                                                ),
                                            ],
                                        ),
                                        dcc.Dropdown(
                                            id="dd-bar",
                                            placeholder="Digite o nome, rua ou bairro...",
                                            clearable=True,
                                            searchable=True,
                                            options=BUSCADOR_BARES.obter_opcoes_iniciais(40),
                                            style={"fontSize": "13px", "borderRadius": "10px"},
                                        ),
                                    ]
                                ),
                                html.Hr(className="divider"),
                                # PASSO 3: RAIO E BUSCA
                                html.Div(
                                    children=[
                                        html.Div(
                                            className="step-header",
                                            children=[
                                                html.Span("3", className="step-number"),
                                                html.Span(
                                                    "Raio de atendimento (km)",
                                                    className="step-title",
                                                ),
                                            ],
                                        ),
                                        dcc.Input(
                                            id="inp-raio",
                                            type="number",
                                            value=2.0,
                                            min=0.1,
                                            max=50.0,
                                            step=0.1,
                                            className="custom-input",
                                            style={"marginBottom": "8px"},
                                        ),
                                        dcc.Loading(
                                            id="loading-buscar",
                                            type="dot",
                                            color="#EA1D2C",
                                            children=[
                                                html.Button(
                                                    "🔍 Buscar Entregadores",
                                                    id="btn-buscar",
                                                    n_clicks=0,
                                                    className="btn-primary",
                                                    style={"padding": "11px"},
                                                )
                                            ],
                                        ),
                                    ]
                                ),
                                dcc.Loading(
                                    id="loading-status",
                                    type="circle",
                                    color="#EA1D2C",
                                    children=[
                                        html.Div(
                                            className="status-box",
                                            children=[
                                                html.Span("🛵", style={"fontSize": "18px"}),
                                                html.Div(
                                                    id="status",
                                                    children="Sistema pronto para gerar entregadores.",
                                                    className="status-text",
                                                ),
                                            ],
                                        )
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="map-container",
                            children=[
                                dcc.Loading(
                                    id="loading-mapa",
                                    type="circle",
                                    color="#EA1D2C",
                                    children=[
                                        dcc.Graph(
                                            id="mapa",
                                            figure=criar_mapa([], None, set()),
                                            config={"displayModeBar": False},
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="table-section",
                    children=[
                        html.H4(
                            "Entregadores Próximos Encontrados",
                            className="table-title",
                        ),
                        dash_table.DataTable(
                            id="tabela",
                            columns=[
                                {"name": "ID", "id": "id"},
                                {"name": "Bairro Oficial", "id": "bairro"},
                                {
                                    "name": "Distância Linha Reta (km)",
                                    "id": "dist",
                                },
                                {"name": "Tempo Estimado", "id": "tempo"},
                                {"name": "Geohash", "id": "gh"},
                            ],
                            data=[],
                            style_cell={
                                "textAlign": "center",
                                "padding": "10px",
                                "fontFamily": "inherit",
                                "fontSize": "13px",
                            },
                            style_header={
                                "fontWeight": "600",
                                "backgroundColor": "#FAFAFA",
                                "color": "#4A4A4A",
                                "borderBottom": "2px solid #EFEFEF",
                            },
                            style_data_conditional=[{
                                "if": {"row_index": 0},
                                "backgroundColor": "#FEE5E7",
                                "fontWeight": "bold",
                            }],
                            page_size=8,
                        ),
                    ],
                ),
            ],
        ),
        dcc.Store(id="store-entregadores", data=[]),
        dcc.Store(id="store-bar", data=None),
    ],
)

# -------------------------------------------------------
# Callbacks do Dash
# -------------------------------------------------------


@app.callback(
    Output("dd-bar", "options"),
    Input("dd-bar", "search_value"),
    State("dd-bar", "value"),
)
def atualizar_opcoes_dropdown(termo_pesquisa, valor_atual):
    """
    Garante que as opções buscadas apareçam e que o bar selecionado 
    não seja descartado pelo Dash quando o campo de pesquisa é limpo.
    """
    if not termo_pesquisa:
        opcoes = BUSCADOR_BARES.obter_opcoes_iniciais(40)
    else:
        opcoes = BUSCADOR_BARES.buscar(termo_pesquisa, limite=60)

    # Se já há um bar selecionado, preserva ele na lista para o Dash não desmarcar
    if valor_atual is not None and 0 <= valor_atual < len(BARES):
        ja_esta_nas_opcoes = any(op["value"] == valor_atual for op in opcoes)
        if not ja_esta_nas_opcoes:
            bar_selecionado = BARES[valor_atual]
            opcoes.insert(
                0,
                {
                    "label": BUSCADOR_BARES.formatar_rotulo(bar_selecionado),
                    "value": valor_atual,
                },
            )

    return opcoes


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
        fig = criar_mapa(entregadores or [], None, set())
        return None, fig

    bar = BARES[idx]
    raio = float(raio or 2.0)
    fig = criar_mapa(entregadores or [], bar, set(), raio_km=raio)
    return bar, fig


@app.callback(
    Output("store-entregadores", "data"),
    Output("mapa", "figure"),
    Output("status", "children"),
    Output("tabela", "data", allow_duplicate=True),
    Input("btn-gerar", "n_clicks"),
    State("inp-qtd", "value"),
    State("store-bar", "data"),
    State("inp-raio", "value"),
    prevent_initial_call=True,
)
def cb_gerar(n_clicks, quantidade, bar, raio):
    try:
        qtd_limpa = int(quantidade)
        if qtd_limpa <= 0:
            qtd_limpa = 1
    except (TypeError, ValueError):
        qtd_limpa = 150

    entregadores_gerados = armazenar_dados_entregadores(N=qtd_limpa, bares=BARES_DICT)

    raio_val = float(raio or 2.0) if bar else None
    fig = criar_mapa(entregadores_gerados, bar, set(), raio_km=raio_val)

    return (
        entregadores_gerados,
        fig,
        f"Sucesso: {len(entregadores_gerados)} entregadores distribuídos na malha viária.",
        [],
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
        return dash.no_update, [], "Gere os entregadores no Passo 1 primeiro."
    if not bar:
        return dash.no_update, [], "Selecione um restaurante no Passo 2 antes de buscar."

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
        f"{len(encontrados)} entregadores no raio | Menor rota:"
        f" {dist_rota_km:.2f} km"
        if id_mais_proximo
        else "Nenhum entregador no raio selecionado."
    )

    return fig, linhas, msg


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="127.0.0.1", port=porta)