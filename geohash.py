# Alfabeto base32 do padrão Geohash (sem as letras a, i, l, o para evitar confusão)
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode(latitude, longitude, precisao=8):
    """
    Converte um par de coordenadas em Geohash.

    Parâmetros:
        latitude  : valor entre -90  e +90
        longitude : valor entre -180 e +180
        precisao  : número de caracteres do resultado (entre 1 e 8)

    Retorna:
        string com o Geohash de comprimento igual a 'precisao'
    """
    # --- Validação das entradas ---
    if not (-90 <= latitude <= 90):
        raise ValueError(f"Latitude inválida: {latitude}. Deve estar entre -90 e 90.")
    if not (-180 <= longitude <= 180):
        raise ValueError(f"Longitude inválida: {longitude}. Deve estar entre -180 e 180.")
    if not (1 <= precisao <= 8):
        raise ValueError(f"Precisão inválida: {precisao}. Deve estar entre 1 e 8.")

    # --- Intervalos iniciais ---
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0

    bits = []

    # --- Geração dos bits por divisão binária intercalada ---
    # Cada caractere do Geohash representa 5 bits.
    # Os bits de índice par  (0, 2, 4 ...) codificam a longitude.
    # Os bits de índice ímpar (1, 3, 5 ...) codificam a latitude.
    for i in range(5 * precisao):
        if i % 2 == 0:
            # Bit de longitude: divide o intervalo de lon ao meio
            meio = (lon_min + lon_max) / 2
            if longitude >= meio:
                bits.append(1)
                lon_min = meio      # ponto está na metade direita
            else:
                bits.append(0)
                lon_max = meio      # ponto está na metade esquerda
        else:
            # Bit de latitude: divide o intervalo de lat ao meio
            meio = (lat_min + lat_max) / 2
            if latitude >= meio:
                bits.append(1)
                lat_min = meio      # ponto está na metade superior
            else:
                bits.append(0)
                lat_max = meio      # ponto está na metade inferior

    # --- Conversão dos bits para caracteres base32 ---
    # Agrupamos os bits de 5 em 5 e convertemos cada grupo em um índice.
    geohash = ""
    for i in range(0, 5 * precisao, 5):
        grupo = bits[i : i + 5]

        # Converter 5 bits em inteiro: ex. [1,1,0,1,0] → 26
        indice = 0
        for bit in grupo:
            indice = indice * 2 + bit

        geohash += BASE32[indice]

    return geohash
