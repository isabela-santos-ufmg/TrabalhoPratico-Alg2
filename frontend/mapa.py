import math
import plotly.graph_objects as go


def pontos_circulo(lat_c, lon_c, raio_km, n=80):
    lats = []
    lons = []
    R = 6371.0

    lat_c_rad = math.radians(lat_c)
    lon_c_rad = math.radians(lon_c)
    distancia_angular = raio_km / R

    for i in range(n + 1):
        angulo = math.radians(i * 360 / n)

        lat_rad = math.asin(
            math.sin(lat_c_rad) * math.cos(distancia_angular)
            + math.cos(lat_c_rad) * math.sin(distancia_angular) * math.cos(angulo)
        )

        lon_rad = lon_c_rad + math.atan2(
            math.sin(angulo) * math.sin(distancia_angular) * math.cos(lat_c_rad),
            math.cos(distancia_angular) - math.sin(lat_c_rad) * math.sin(lat_rad),
        )

        lats.append(math.degrees(lat_rad))
        lons.append(math.degrees(lon_rad))

    return lats, lons


def criar_mapa(
    entregadores,
    bar,
    ids_encontrados,
    raio_km=None,
    rota_coords=None,
    id_mais_proximo=None,
):
    fig = go.Figure()

    fig.add_trace(go.Scattermap(lat=[], lon=[], mode="markers", showlegend=False))

    # Entregadores fora do raio terão cor verde complementar ao vermelho da paleta principal
    fora = [e for e in entregadores if e["id"] not in ids_encontrados]
    if fora:
        fig.add_trace(
            go.Scattermap(
                lat=[e["lat"] for e in fora],
                lon=[e["lon"] for e in fora],
                mode="markers",
                marker=dict(size=9, color="#10B981", symbol="circle"),
                hovertext=[
                    f"<b>Entregador {e['id']}</b><br>Status: Disponível" for e in fora
                ],
                hoverinfo="text",
                name="Entregadores Disponíveis",
            )
        )

    # Entregadores dentro do raio terão cor vermelha complementar ao verde da paleta principal
    dentro = [
        e
        for e in entregadores
        if e["id"] in ids_encontrados and e["id"] != id_mais_proximo
    ]
    if dentro:
        fig.add_trace(
            go.Scattermap(
                lat=[e["lat"] for e in dentro],
                lon=[e["lon"] for e in dentro],
                mode="markers",
                marker=dict(size=14, color="#EA1D2C", symbol="circle"),
                hovertext=[
                    f"<b>Entregador {e['id']}</b><br>✓ No raio de atendimento"
                    for e in dentro
                ],
                hoverinfo="text",
                name="No Raio de Atendimento",
            )
        )

    # Entregador mais próximo terá cor vermelha mais escura
    mais_proximo = next(
        (e for e in entregadores if e["id"] == id_mais_proximo), None
    )
    if mais_proximo:
        fig.add_trace(
            go.Scattermap(
                lat=[mais_proximo["lat"]],
                lon=[mais_proximo["lon"]],
                mode="markers+text",
                marker=dict(size=18, color="#991B1B", symbol="circle"),
                text=["B"],
                textposition="middle center",
                textfont=dict(size=11, color="white", weight="bold"),
                hovertext=[
                    f"<b>★ Ponto B: Mais Próximo</b><br>ID: {mais_proximo['id']}"
                ],
                hoverinfo="text",
                name="Entregador Mais Próximo",
            )
        )

    if rota_coords and len(rota_coords[0]) > 0:
        r_lats, r_lons = rota_coords
        fig.add_trace(
            go.Scattermap(
                lat=r_lats,
                lon=r_lons,
                mode="lines",
                line=dict(width=5, color="#EA1D2C"),
                hoverinfo="text",
                hovertext="Trajeto do entregador mais próximo até o restaurante",
                name="Trajeto até o Bar",
            )
        )

    if bar and raio_km:
        b_lat = bar.get("lat") or bar.get("latitude")
        b_lon = bar.get("lon") or bar.get("longitude")
        lats_c, lons_c = pontos_circulo(b_lat, b_lon, raio_km)

        fig.add_trace(
            go.Scattermap(
                lat=lats_c,
                lon=lons_c,
                mode="lines",
                line=dict(color="rgba(234, 29, 44, 0.4)", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    if bar:
        b_lat = bar.get("lat") or bar.get("latitude")
        b_lon = bar.get("lon") or bar.get("longitude")

        hover_bar = (
            f"<b>Ponto A: {bar.get('nome', 'Restaurante')}</b><br>"
            f"{bar.get('logradouro', '')}<br>"
            f"Bairro: {bar.get('bairro', 'BH')}"
        )
        fig.add_trace(
            go.Scattermap(
                lat=[b_lat],
                lon=[b_lon],
                mode="markers+text",
                marker=dict(size=22, color="#1E1E1E", symbol="circle"),
                text=["A"],
                textposition="middle center",
                textfont=dict(size=12, color="white", weight="bold"),
                hovertext=[hover_bar],
                hoverinfo="text",
                name="Restaurante Selecionado",
            )
        )

    if bar:
        centro_lat = bar.get("lat") or bar.get("latitude")
        centro_lon = bar.get("lon") or bar.get("longitude")
        zoom = (
            max(9.5, min(15.0, 14.5 - math.log2(max(raio_km, 0.4))))
            if raio_km
            else 13.0
        )
    else:
        centro_lat, centro_lon = -19.92, -43.95
        zoom = 11.5

    fig.update_layout(
        map_style="carto-positron",
        map_center={"lat": centro_lat, "lon": centro_lon},
        map_zoom=zoom,
        height=620,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend=dict(
            orientation="h",
            y=1.02,
            x=0,
            bgcolor="rgba(255,255,255,0.9)",
            font=dict(family="sans-serif", size=11),
        ),
        uirevision="mapa",
    )
    return fig