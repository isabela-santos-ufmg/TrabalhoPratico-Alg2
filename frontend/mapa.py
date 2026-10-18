import math
import plotly.graph_objects as go

def pontos_circulo(lat_c, lon_c, raio_km, n=60):
    lats = []
    lons = []
    
    # Raio médio da Terra em quilómetros
    R = 6371.0
    
    # Converter latitude e longitude do centro para radianos
    lat_c_rad = math.radians(lat_c)
    lon_c_rad = math.radians(lon_c)
    
    # Distância angular em radianos (raio dividido pelo raio da Terra)
    angular_distance = raio_km / R
    
    for i in range(n + 1):
        # Ângulo de rotação em torno do centro (de 0 a 360 graus)
        angulo = math.radians(i * 360 / n)
        
        # Fórmula esférica inversa para encontrar a latitude do ponto no perímetro
        lat_rad = math.asin(
            math.sin(lat_c_rad) * math.cos(angular_distance) +
            math.cos(lat_c_rad) * math.sin(angular_distance) * math.cos(angulo)
        )
        
        # Fórmula esférica inversa para encontrar a longitude do ponto no perímetro
        lon_rad = lon_c_rad + math.atan2(
            math.sin(angulo) * math.sin(angular_distance) * math.cos(lat_c_rad),
            math.cos(angular_distance) - math.sin(lat_c_rad) * math.sin(lat_rad)
        )
        
        # Converter de volta para graus e guardar nas listas
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

    fora = [e for e in entregadores if e["id"] not in ids_encontrados]
    if fora:
        fig.add_trace(
            go.Scattermap(
                lat=[e["lat"] for e in fora],
                lon=[e["lon"] for e in fora],
                mode="markers",
                marker=dict(size=9, color="#2A9D8F", symbol="circle"),
                hovertext=[f"Entregador {e['id']}" for e in fora],
                hoverinfo="text",
                name="Entregadores Disponíveis",
            )
        )

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
                marker=dict(size=14, color="#E76F51", symbol="circle"),
                hovertext=[f"Entregador {e['id']} (No raio) ✓" for e in dentro],
                hoverinfo="text",
                name="No Raio de Atendimento",
            )
        )

    mais_proximo = next((e for e in entregadores if e["id"] == id_mais_proximo), None)
    if mais_proximo:
        fig.add_trace(
            go.Scattermap(
                lat=[mais_proximo["lat"]],
                lon=[mais_proximo["lon"]],
                mode="markers+text",
                marker=dict(size=18, color="#8338EC", symbol="circle"),
                text=["Mais Próximo"],
                textposition="bottom right",
                hovertext=[f"★ Entregador Mais Próximo: ID {mais_proximo['id']}"],
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
                line=dict(width=5, color="#1D4ED8"),
                hoverinfo="text",
                hovertext="Rota viária mais curta (pelas ruas de BH)",
                name="Trajeto até o Bar",
            )
        )

    if bar and raio_km:
        lats_c, lons_c = pontos_circulo(bar["lat"], bar["lon"], raio_km)
        fig.add_trace(
            go.Scattermap(
                lat=lats_c,
                lon=lons_c,
                mode="lines",
                line=dict(color="rgba(231, 111, 81, 0.6)", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    if bar:
        hover_bar = (
            f"<b>{bar['nome']}</b><br>"
            f"{bar.get('logradouro', '')}<br>"
            f"Bairro: {bar.get('bairro', 'BH')}"
        )
        fig.add_trace(
            go.Scattermap(
                lat=[bar["lat"]],
                lon=[bar["lon"]],
                mode="markers+text",
                marker=dict(size=20, color="#D90429", symbol="restaurant"),
                text=[bar["nome"][:25]],
                textposition="top right",
                textfont=dict(size=12, color="#900C3F"),
                hovertext=[hover_bar],
                hoverinfo="text",
                name="Bar Selecionado",
            )
        )

    centro_lat = bar["lat"] if bar else -19.92
    centro_lon = bar["lon"] if bar else -43.95

    fig.update_layout(
        map_style="open-street-map",
        map_center={"lat": centro_lat, "lon": centro_lon},
        map_zoom=12 if bar else 11,
        height=560,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend=dict(
            orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"
        ),
        uirevision="mapa",
    )
    return fig