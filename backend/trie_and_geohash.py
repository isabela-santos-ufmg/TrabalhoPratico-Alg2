from backend.geohash import encode, vizinhos
from backend.trie import Trie

def construir_trie(entregadores):
    t = Trie()
    for e in entregadores:
        gh = encode(e["lat"], e["lon"], 8)
        t.addNode(gh, e)
    return t

def buscar_entregadores_com_bordas(trie, lat, lon, raio_km, haversine_func, precisao=None):
    if precisao is None:
        precisao = 6 if raio_km <= 1.2 else 5

    gh = encode(lat, lon, precisao)
    celulas = vizinhos(gh)
    candidatos = {}

    for celula in celulas:
        for entregador in trie.searchNode(celula):
            candidatos[entregador["id"]] = entregador

    resultado = []
    for entregador in candidatos.values():
        distancia = haversine_func(lat, lon, entregador["lat"], entregador["lon"])
        if distancia <= raio_km:
            resultado.append(entregador)

    return resultado