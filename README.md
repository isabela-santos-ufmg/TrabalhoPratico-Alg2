# TrabalhoPratico-Alg2: Indexação Geoespacial e Geometria Computacional Híbrida

Neste trabalho, são abordados os aspectos práticos da integração entre estruturas de dados para tratamento de strings (Árvores Trie Compactas / Patricia Tries) aplicadas à codificação Geohash, além de algoritmos de geometria computacional voltados a sistemas de rastreamento de frotas e serviços de geolocalização em tempo real para a cidade de Belo Horizonte.

---

## Fontes de Dados Oficiais e Referências
* **Limites do Município de BH:** [Metadados na Dados PBH](https://dados.pbh.gov.br/pt_BR/dataset/limite-municipio)
* **Limites Geográficos dos Bairros de BH:** [GeoServiços PBH](https://forest-gis.com/gis-resources/bairros-de-belo-horizonte-mg-fonte-geoservicos-pbh-gov-br/)
* **Bounding Box de Belo Horizonte:** [Topographic Map](https://pt-br.topographic-map.com/map-vc85k/Belo-Horizonte/?center=-20.02638%2C-43.49281&zoom=9)

---

## Pré-requisitos e Instalação

Para rodar este projeto com facilidade, utilizamos um `Makefile` automatizado que gerencia o ambiente virtual do Python, as dependências e a execução do sistema.

### 1. Instalação do `make`
Caso você não possua o `make` instalado no seu sistema operacional, veja abaixo como proceder:

* **No Ubuntu / Debian:**
  Siga o guia passo a passo oficial de instalação: [Tutorial GeeksforGeeks para Instalar o Make no Ubuntu](https://www.geeksforgeeks.org/installation-guide/how-to-install-make-on-ubuntu/). Em resumo, você pode rodar no terminal:
  ```bash
  sudo apt update
  sudo apt install make
**No MacOS:**
  ```bash
  xcode-select --install
```
### 2. Pyenv
O projeto gerencia versões específicas do Python através do pyenv. Se você não tiver o pyenv instalado em sua máquina, o comando do Makefile foi estruturado para auxiliar na verificação, mas é recomendável instalá-lo previamente para garantir a compatibilidade correta da versão do Python especificada (3.10.12).
 ```bash
make install-pyenv
```
### 3. Rodar o Programa 
Abra o terminal na raiz do programa e rode:
 ```bash
make run
```
O comando acima irá automaticamente:

- Verificar/instalar a versão correta do Python via pyenv (caso configurado).

- Criar o ambiente virtual isolado (.venv).

- Instalar todas as dependências necessárias do projeto (incluindo osmnx, networkx, pandas, geopandas, dash, etc.).

- Limpar arquivos temporários anteriores (como bases antigas de entregadores).

- Iniciar o servidor web local do painel interativo Dash na porta 8050.

Para acessar, abra o navegador e acesse: <http://127.0.0.1:8050>
