import os
import pandas as pd


def carregar_bares(caminho="data/output/bares_com_geohash.xlsx"):
  if not os.path.exists(caminho):
    caminho_csv = (
        caminho.replace(".xlsx", ".csv")
        if caminho.endswith(".xlsx")
        else caminho
    )
    if os.path.exists(caminho_csv):
      caminho = caminho_csv
    else:
      print(f"[AVISO] Arquivo de bares '{caminho}' não encontrado.")
      return {}

  df = (
      pd.read_excel(caminho)
      if caminho.endswith((".xlsx", ".xls"))
      else pd.read_csv(caminho)
  )
  df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

  def limpar_texto(valor):
    if pd.isna(valor):
      return ""
    texto = str(valor).strip()
    return "" if texto.lower() in ("nan", "none", "null") else texto

  bares_dict = {}

  for idx, linha in df.iterrows():
    bar_id = int(linha.get("_id", idx + 1))
    fantasia = limpar_texto(linha.get("NOME_FANTASIA"))
    razao = limpar_texto(linha.get("NOME"))
    bairro = limpar_texto(linha.get("NOME_BAIRRO"))
    desc_log = limpar_texto(linha.get("DESC_LOGRADOURO"))
    nome_log = limpar_texto(linha.get("NOME_LOGRADOURO"))
    numero = limpar_texto(linha.get("NUMERO_IMOVEL"))

    # Monta endereço amigável curto (ex: "RUA DO OURO, 1428")
    endereco_curto = f"{desc_log} {nome_log}".strip()
    if numero:
      endereco_curto += f", {numero}"

    # Nome prioritário: Fantasia > Razão Social > Logradouro
    nome_principal = fantasia or razao or endereco_curto or f"Bar {bar_id}"

    # Rótulo rico para o Dropdown (ex: "BAR DO FABIO — RUA DOS AIMORES (FUNCIONARIOS)")
    complementos = []
    if endereco_curto:
      complementos.append(endereco_curto)
    if bairro:
      complementos.append(bairro)

    rotulo_dropdown = (
        f"{nome_principal} — {' - '.join(complementos)}"
        if complementos
        else nome_principal
    )

    bares_dict[bar_id] = {
        "id": bar_id,
        "nome": nome_principal,
        "rotulo_dropdown": rotulo_dropdown,
        "nome_fantasia": fantasia,
        "razao_social": razao,
        "bairro": bairro,
        "logradouro": endereco_curto,
        "endereco_completo": limpar_texto(linha.get("ENDERECO_CONSULTADO")),
        "lat": float(linha["LATITUDE"]),
        "lon": float(linha["LONGITUDE"]),
        "latitude": float(linha["LATITUDE"]),
        "longitude": float(linha["LONGITUDE"]),
        "geohash": str(linha.get("GEOHASH", "")),
    }

  print(f"[SUCESSO] {len(bares_dict)} bares carregados com sucesso.")
  return bares_dict