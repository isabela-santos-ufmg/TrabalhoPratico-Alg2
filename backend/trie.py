import re
import unicodedata


class Node:
    __slots__ = ("rotulo", "filhos", "valores")

    def __init__(self, rotulo: str = ""):
        self.rotulo = rotulo
        self.filhos = {}
        self.valores = []


class Trie:

    def __init__(self):
        self.root = Node(rotulo="")
        self.total_nos = 1

    @staticmethod
    def longest_prefix(s1: str, s2: str) -> int:
        limite = min(len(s1), len(s2))
        for i in range(limite):
            if s1[i] != s2[i]:
                return i
        return limite

    def addNode(self, chave: str, dado: any):
        atual = self.root
        restante = chave

        while restante:
            primeira_letra = restante[0]
            filho = atual.filhos.get(primeira_letra)

            if filho is None:
                novo_no = Node(rotulo=restante)
                novo_no.valores.append(dado)
                atual.filhos[primeira_letra] = novo_no
                self.total_nos += 1
                return

            l = self.longest_prefix(restante, filho.rotulo)

            if l == len(filho.rotulo):
                restante = restante[l:]
                atual = filho
                if not restante:
                    atual.valores.append(dado)
                    return
            else:
                prefixo_comum = filho.rotulo[:l]
                sufixo_filho = filho.rotulo[l:]
                sufixo_restante = restante[l:]

                no_intermediario = Node(rotulo=prefixo_comum)
                filho.rotulo = sufixo_filho
                no_intermediario.filhos[sufixo_filho[0]] = filho

                if sufixo_restante:
                    nova_folha = Node(rotulo=sufixo_restante)
                    nova_folha.valores.append(dado)
                    no_intermediario.filhos[sufixo_restante[0]] = nova_folha
                    self.total_nos += 2
                else:
                    no_intermediario.valores.append(dado)
                    self.total_nos += 1

                atual.filhos[primeira_letra] = no_intermediario
                return

    def searchNode(self, prefixo: str) -> list:
        if not prefixo:
            return []

        atual = self.root
        restante = prefixo

        while restante:
            primeira_letra = restante[0]
            filho = atual.filhos.get(primeira_letra)

            if not filho:
                return []

            l = self.longest_prefix(restante, filho.rotulo)

            if l == len(filho.rotulo):
                restante = restante[l:]
                atual = filho
            elif l == len(restante):
                return self.coletar(filho)
            else:
                return []

        return self.coletar(atual)

    def coletar(self, node: Node) -> list:
        resultado = []
        pilha = [node]
        while pilha:
            n = pilha.pop()
            resultado.extend(n.valores)
            pilha.extend(n.filhos.values())
        return resultado


class TrieTextualBares(Trie):

    def __init__(self, bares: any = None):
        super().__init__()
        if isinstance(bares, dict):
            self.bares = list(bares.values())
        else:
            self.bares = bares or []

        if self.bares:
            self.indexar_catalogo()

    @staticmethod
    def normalizar(texto: str) -> str:
        if not texto:
            return ""
        texto = str(texto).strip().lower()
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = re.sub(r"[^\w\s]", "", texto)
        return " ".join(texto.split())

    @staticmethod
    def obter_nome_apresentacao(bar: dict) -> str:
        """Extrai prioritariamente o Nome Fantasia; se vazio, usa a Razão Social (NOME)."""
        fantasia = str(
            bar.get("nome_fantasia") or bar.get("NOME_FANTASIA") or ""
        ).strip()
        if fantasia and fantasia.upper() not in ("NAN", "NONE", ""):
            return fantasia

        razao = str(bar.get("razao_social") or bar.get("NOME") or "").strip()
        if razao and razao.upper() not in ("NAN", "NONE", ""):
            return razao

        return str(bar.get("nome", f"Bar {bar.get('id', '')}")).strip()

    def indexar_bar(self, bar: dict, indice: int):
        nome = self.obter_nome_apresentacao(bar)
        razao = str(bar.get("razao_social") or bar.get("NOME") or "")
        rua = str(bar.get("logradouro") or bar.get("NOME_LOGRADOURO") or "")
        bairro = str(bar.get("bairro") or bar.get("NOME_BAIRRO") or "")

        texto_completo = f"{nome} {razao} {rua} {bairro}"
        texto_norm = self.normalizar(texto_completo)

        for palavra in texto_norm.split():
            if len(palavra) >= 2:
                self.addNode(palavra, indice)

        nome_sem_espaco = self.normalizar(nome).replace(" ", "")
        if len(nome_sem_espaco) >= 3:
            self.addNode(nome_sem_espaco, indice)

    def indexar_catalogo(self):
        for idx, bar in enumerate(self.bares):
            self.indexar_bar(bar, idx)

    def formatar_rotulo(self, bar: dict) -> str:
        nome = self.obter_nome_apresentacao(bar)
        bairro = str(bar.get("bairro") or bar.get("NOME_BAIRRO") or "").strip()
        rua = str(bar.get("logradouro") or bar.get("NOME_LOGRADOURO") or "").strip()

        detalhes = [d for d in [rua, bairro] if d and d.upper() != "NAN"]
        if detalhes:
            return f"{nome} — {', '.join(detalhes)}"
        return nome

    def buscar(self, termo: str, limite: int = 50) -> list:
        termo_norm = self.normalizar(termo)
        if not termo_norm or len(termo_norm) < 2:
            return self.obter_opcoes_iniciais(limite)

        palavras = termo_norm.split()
        chave_busca = palavras[-1]

        indices = self.searchNode(chave_busca)
        indices_unicos = list(dict.fromkeys(indices))

        opcoes = []
        for idx in indices_unicos[:limite]:
            bar = self.bares[idx]
            opcoes.append({"label": self.formatar_rotulo(bar), "value": idx})

        return opcoes

    def obter_opcoes_iniciais(self, limite: int = 40) -> list:
        opcoes = []
        for idx, bar in enumerate(self.bares[:limite]):
            opcoes.append({"label": self.formatar_rotulo(bar), "value": idx})
        return opcoes