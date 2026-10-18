import os
import osmnx as ox

GRAFO_CACHE = "data/output/grafo_bh.graphml"

def carregar_grafo_bh():
    if os.path.exists(GRAFO_CACHE):
        print("[DEBUG] Carregando grafo viário de BH do arquivo GraphML local...")
        grafo = ox.load_graphml(GRAFO_CACHE)
        print("[DEBUG] Grafo carregado com sucesso!")
        return grafo

    print("[DEBUG] Baixando malha viária de Belo Horizonte (isso pode demorar na primeira vez)...")
    os.makedirs(os.path.dirname(GRAFO_CACHE), exist_ok=True)
    
    grafo = ox.graph_from_place("Belo Horizonte, Minas Gerais, Brazil", network_type="drive")
    
    ox.save_graphml(grafo, filepath=GRAFO_CACHE)
    print("[DEBUG] Grafo baixado e salvo em GraphML!")
    
    return grafo