import numpy as np 
import pandas as pd
import osmnx as ox

"""
esperado que bares dict seja: 
{
    id: 
    latitude:
    longitude:
}
"""
def gerar_entregadores(N: int, bares: dict) -> tuple:
    lat, lon = [], []
    origem_bares = [] 
    
    qtd_bares = len(bares)
    if qtd_bares == 0:
        return lat, lon, origem_bares
    
    qtd_entregadores_por_bar = N // qtd_bares 
    resto = N % qtd_bares

    desvio_padrao = 0.01
    
    for i, (bar_id, bar) in enumerate(bares.items()):
        tamanho_grupo = qtd_entregadores_por_bar + 1 if i < resto else qtd_entregadores_por_bar
        lat_bar = bar['latitude']
        lon_bar = bar['longitude']

        # gera populacao do tamamnho de cada grupo em torno do bar normalmente distribuida em torno da latitude e longitude do bar em questao
        distribuicao_latitude = np.random.normal(loc=lat_bar, scale=desvio_padrao, size=tamanho_grupo)
        distribuicao_longitude = np.random.normal(loc=lon_bar, scale=desvio_padrao, size=tamanho_grupo)
        
        lat.extend(distribuicao_latitude)
        lon.extend(distribuicao_longitude)
        origem_bares.extend([bar_id] * tamanho_grupo) # Associa cada entregador ao seu bar central

    return np.array(lat), np.array(lon), origem_bares

def corrigir_coordenadas(distribuicao_latitude: np.ndarray, distribuicao_longitude: np.ndarray):
    malha = ox.graph_from_place("Belo Horizonte, Minas Gerais, Brazil", network_type="drive") # malha de ruas de bh
    coordenadas_corrigidas = ox.distance.nearest_nodes(malha, X=distribuicao_longitude, Y=distribuicao_latitude) # retorna os nós mais próximos das coordenadas dos entregadores
    return malha, coordenadas_corrigidas

def armazenar_dados_entregadores(N, bares: dict):
    distribuicao_latitude, distribuicao_longitude, origens = gerar_entregadores(N, bares=bares)
    if len(distribuicao_latitude) == 0 or len(distribuicao_longitude) == 0:
        print("Nenhum entregador gerado. Verifique se há bares disponíveis.")
        return
    
    malha, coordenadas_corrigidas = corrigir_coordenadas(distribuicao_latitude, distribuicao_longitude)
    
    entregadores = []
    # criar dict com coordenadas dos entregadores
    for id_global, (node_id, bar_origem) in enumerate(zip(coordenadas_corrigidas, origens)):
        dados_node = malha.nodes[node_id]
        entregadores.append({
            'id': id_global, 
            'latitude': dados_node['y'],
            'longitude': dados_node['x'],
            'id_bar_central': bar_origem
        })

    df = pd.DataFrame(entregadores)
    df.to_csv("entregadores.csv", index=False, encoding="utf-8")
    return entregadores

if __name__ == "__main__":
    # Dicionário de exemplo de bares em Belo Horizonte
    bares_exemplo = {
        1: {
            "id": 1,
            "latitude": -19.9322,
            "longitude": -43.9381
        },
        2: {
            "id": 2,
            "latitude": -19.9392,
            "longitude": -43.9335
        },
        3: {
            "id": 3,
            "latitude": -19.9281,
            "longitude": -43.9405
        }
    }

    print("Iniciando o teste de geração e correção de entregadores...")
    
    # Chama a função principal passando 30 entregadores e os bares de exemplo
    entregadores_gerados = armazenar_dados_entregadores(N=30, bares=bares_exemplo)
    
    if entregadores_gerados:
        print(f"\nTeste concluído com sucesso!")
        print(f"Total de entregadores gerados e corrigidos: {len(entregadores_gerados)}")
        print("Exemplo dos 2 primeiros entregadores:")
        for e in entregadores_gerados[:2]:
            print(e)



