import networkx as nx
import osmnx as ox

def calcular_rota_viaria(grafo, lat_origem, lon_origem, lat_destino, lon_destino):
  try:
    no_origem = ox.distance.nearest_nodes(grafo, X=lon_origem, Y=lat_origem)
    no_destino = ox.distance.nearest_nodes(grafo, X=lon_destino, Y=lat_destino)

    if no_origem == no_destino:
      return [lat_origem, lat_destino], [lon_origem, lon_destino], 0.0

    rota_nos = nx.shortest_path(grafo, no_origem, no_destino, weight="length")

    lats_rota = []
    lons_rota = []
    distancia_total = 0.0

    for u, v in zip(rota_nos[:-1], rota_nos[1:]):
      dados_arestas = grafo.get_edge_data(u, v)
      if dados_arestas:
        aresta = min(dados_arestas.values(), key=lambda d: d.get("length", 1.0))
        distancia_total += aresta.get("length", 0.0)

        if "geometry" in aresta:
          xs, ys = aresta["geometry"].xy
          lons_rota.extend(xs)
          lats_rota.extend(ys)
        else:
          lats_rota.extend([grafo.nodes[u]["y"], grafo.nodes[v]["y"]])
          lons_rota.extend([grafo.nodes[u]["x"], grafo.nodes[v]["x"]])

    return lats_rota, lons_rota, distancia_total

  except nx.NetworkXNoPath:
    print("[AVISO] Não há rota conectada entre a origem e o destino.")
    return [], [], 0.0
  except Exception as e:
    print(f"[ERRO] Falha no roteamento: {e}")
    return [], [], 0.0