import numpy as np 
import pandas as pd

"""
esperado que bares dict seja: 
{
    id: 
    latitude:
    longitude:
}
"""
def gerar_entregadores(N: int, bares: dict) -> dict:
    entregadores = {}
    qtd_bares = len(bares)
    if qtd_bares == 0:
        return entregadores
    
    qtd_entregadores_por_bar = N // qtd_bares 
    resto = N % qtd_bares

    desvio_padrao = 0.01
    id_global = 0
    
    for i, (bar_id, bar) in enumerate(bares.items()):
        tamanho_grupo = qtd_entregadores_por_bar + 1 if i < resto else qtd_entregadores_por_bar
        lat_bar = bar['latitude']
        lon_bar = bar['longitude']

        # gera populacao do tamamnho de cada grupo em torno do bar normalmente distribuida em torno da latitude e longitude do bar em questao
        distribuicao_latitude = np.random.normal(loc=lat_bar, scale=desvio_padrao, size=tamanho_grupo)
        distribuicao_longitude = np.random.normal(loc=lon_bar, scale=desvio_padrao, size=tamanho_grupo)

        # criar dict com coordenadas dos entregadoes
        for j in range(len(distribuicao_latitude)):
            lat_entregador = distribuicao_latitude[j]
            lon_entregador = distribuicao_longitude[j]

            entregadores.append({
                'id': id_global, 
                'latitude': lat_entregador,
                'longitude': lon_entregador,
                'id_bar_central': bar['id']
            })
            id_global+=1
    return entregadores

    def armazenar_dados_entregadores():
        entregadores = gerar_entregadores()
        df = pd.Dataframe(entregadoes)
        df.to_csv("entregadores.csv", index=False, encoding="utf-8")






