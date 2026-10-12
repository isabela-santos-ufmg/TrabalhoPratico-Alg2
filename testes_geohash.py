import unittest
from geohash import encode


class TestGeohash(unittest.TestCase):

    # ------------------------------------------------------------------
    # Coordenadas conhecidas com resultado verificado
    # ------------------------------------------------------------------

    def test_exemplo_classico(self):
        # Exemplo da Wikipedia: (57.64911, 10.40744) → "u4pruydq"
        self.assertEqual(encode(57.64911, 10.40744, 8), "u4pruydq")

    def test_origem_precisao_1(self):
        # A origem exata (0, 0) com precisão 1 deve gerar 's'
        self.assertEqual(encode(0, 0, 1), "s")

    def test_origem_precisao_8(self):
        # A origem (0, 0) com precisão máxima
        self.assertEqual(encode(0, 0, 8), "s0000000")

    def test_rio_de_janeiro_precisao_1(self):
        # Coordenadas do centro do Rio de Janeiro
        self.assertEqual(encode(-22.9068, -43.1729, 1), "7")

    def test_rio_de_janeiro_precisao_6(self):
        self.assertEqual(encode(-22.9068, -43.1729, 6), "75cm9t")

    def test_rio_de_janeiro_precisao_8(self):
        self.assertEqual(encode(-22.9068, -43.1729, 8), "75cm9tfq")

    def test_belo_horizonte(self):
        # Centro de Belo Horizonte
        self.assertEqual(encode(-19.9173, -43.9345, 8), "7h2y8npv")

    # ------------------------------------------------------------------
    # Diferentes precisões (1 a 8)
    # ------------------------------------------------------------------

    def test_tamanho_igual_a_precisao(self):
        # O resultado deve ter exatamente 'precisao' caracteres
        for p in range(1, 9):
            with self.subTest(precisao=p):
                resultado = encode(0, 0, p)
                self.assertEqual(len(resultado), p)

    def test_default_e_precisao_8(self):
        # Precisão padrão deve ser 8
        self.assertEqual(encode(0, 0), encode(0, 0, 8))

    # ------------------------------------------------------------------
    # Coordenadas positivas, negativas e iguais a zero
    # ------------------------------------------------------------------

    def test_canto_maximo(self):
        # Canto superior direito: (90, 180) → todos os bits são 1 → 'z'
        self.assertEqual(encode(90, 180, 1), "z")

    def test_canto_minimo(self):
        # Canto inferior esquerdo: (-90, -180) → todos os bits são 0 → '0'
        self.assertEqual(encode(-90, -180, 1), "0")

    def test_hemisferio_norte_leste(self):
        # Verifica que coordenadas positivas geram resultado não vazio
        resultado = encode(51.5074, 0.1278, 5)  # Londres
        self.assertEqual(len(resultado), 5)

    # ------------------------------------------------------------------
    # Propriedade de prefixo
    # ------------------------------------------------------------------

    def test_prefixo_menor_precisao(self):
        # Geohash de precisão 3 deve ser prefixo do de precisão 6
        lat, lon = -22.9068, -43.1729
        gh3 = encode(lat, lon, 3)
        gh6 = encode(lat, lon, 6)
        self.assertTrue(gh6.startswith(gh3))

    def test_prefixo_precisao_1_e_8(self):
        # Geohash de precisão 1 deve ser prefixo do de precisão 8
        lat, lon = 57.64911, 10.40744
        gh1 = encode(lat, lon, 1)
        gh8 = encode(lat, lon, 8)
        self.assertTrue(gh8.startswith(gh1))

    # ------------------------------------------------------------------
    # Todos os caracteres devem pertencer ao alfabeto base32
    # ------------------------------------------------------------------

    def test_caracteres_validos(self):
        base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
        resultado = encode(57.64911, 10.40744, 8)
        for char in resultado:
            self.assertIn(char, base32)

    # ------------------------------------------------------------------
    # Coordenadas inválidas
    # ------------------------------------------------------------------

    def test_latitude_maior_que_90(self):
        with self.assertRaises(ValueError):
            encode(91, 0)

    def test_latitude_menor_que_menos_90(self):
        with self.assertRaises(ValueError):
            encode(-91, 0)

    def test_longitude_maior_que_180(self):
        with self.assertRaises(ValueError):
            encode(0, 181)

    def test_longitude_menor_que_menos_180(self):
        with self.assertRaises(ValueError):
            encode(0, -181)

    # ------------------------------------------------------------------
    # Precisões inválidas
    # ------------------------------------------------------------------

    def test_precisao_zero(self):
        with self.assertRaises(ValueError):
            encode(0, 0, 0)

    def test_precisao_nove(self):
        with self.assertRaises(ValueError):
            encode(0, 0, 9)

    def test_precisao_negativa(self):
        with self.assertRaises(ValueError):
            encode(0, 0, -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
