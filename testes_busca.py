import unittest
from trie import Trie
from geohash import encode, decode
from buscar_entregador import buscar_entregadores, vizinhos, buscar_por_prefixo, haversine

LAT_REST = -19.9
LON_REST = -43.9
P = 6

_lat_c, _lon_c, _lat_err, _lon_err = decode(encode(LAT_REST, LON_REST, P))
LAT_BORDA_NORTE = _lat_c + _lat_err
LON_BORDA_LESTE = _lon_c + _lon_err
EPS = 0.00001


def _trie_com(*entregadores):
    t = Trie()
    for e in entregadores:
        t.addNode(encode(e["lat"], e["lon"], 8), e)
    return t


class TestBuscaEntregador(unittest.TestCase):

    def test_mesma_celula_dentro_raio(self):
        e = {"id": 1, "lat": LAT_REST + 0.0001, "lon": LON_REST}
        t = _trie_com(e)
        resultado = buscar_entregadores(t, LAT_REST, LON_REST, raio_km=1.0, precisao=P)
        self.assertIn(1, [r["id"] for r in resultado])

    def test_celula_adjacente_dentro_raio(self):
        e = {"id": 2, "lat": LAT_BORDA_NORTE + EPS, "lon": LON_REST}
        self.assertNotEqual(encode(e["lat"], e["lon"], P), encode(LAT_REST, LON_REST, P))
        t = _trie_com(e)
        resultado = buscar_entregadores(t, LAT_REST, LON_REST, raio_km=1.0, precisao=P)
        self.assertIn(2, [r["id"] for r in resultado])

    def test_celula_adjacente_fora_raio(self):
        e = {"id": 3, "lat": LAT_BORDA_NORTE + 0.015, "lon": LON_REST}
        t = _trie_com(e)
        resultado = buscar_entregadores(t, LAT_REST, LON_REST, raio_km=1.0, precisao=P)
        self.assertNotIn(3, [r["id"] for r in resultado])

    def test_restaurante_na_borda_entre_duas_celulas(self):
        lat_rest_borda = LAT_BORDA_NORTE - EPS
        e = {"id": 4, "lat": LAT_BORDA_NORTE + EPS, "lon": LON_REST}
        self.assertNotEqual(encode(lat_rest_borda, LON_REST, P), encode(e["lat"], e["lon"], P))
        self.assertLess(haversine(lat_rest_borda, LON_REST, e["lat"], e["lon"]), 0.01)
        t = _trie_com(e)
        resultado = buscar_entregadores(t, lat_rest_borda, LON_REST, raio_km=0.1, precisao=P)
        self.assertIn(4, [r["id"] for r in resultado])

    def test_restaurante_no_canto_de_quatro_celulas(self):
        lat_canto = LAT_BORDA_NORTE - EPS
        lon_canto = LON_BORDA_LESTE - EPS
        d_norte = {"id": 5, "lat": LAT_BORDA_NORTE + EPS, "lon": lon_canto}
        d_leste = {"id": 6, "lat": lat_canto, "lon": LON_BORDA_LESTE + EPS}
        d_ne    = {"id": 7, "lat": LAT_BORDA_NORTE + EPS, "lon": LON_BORDA_LESTE + EPS}
        t = _trie_com(d_norte, d_leste, d_ne)
        resultado = buscar_entregadores(t, lat_canto, lon_canto, raio_km=0.5, precisao=P)
        ids = [r["id"] for r in resultado]
        self.assertIn(5, ids)
        self.assertIn(6, ids)
        self.assertIn(7, ids)

    def test_sem_entregadores_no_raio(self):
        e = {"id": 8, "lat": LAT_REST + 0.1, "lon": LON_REST}
        t = _trie_com(e)
        resultado = buscar_entregadores(t, LAT_REST, LON_REST, raio_km=1.0, precisao=P)
        self.assertEqual(resultado, [])

    def test_sem_duplicatas(self):
        e = {"id": 9, "lat": _lat_c, "lon": _lon_c}
        t = _trie_com(e)
        resultado = buscar_entregadores(t, LAT_REST, LON_REST, raio_km=1.0, precisao=P)
        self.assertEqual([r["id"] for r in resultado].count(9), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
