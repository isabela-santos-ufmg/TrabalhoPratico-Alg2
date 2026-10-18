import numpy as np
import pandas as pd

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

    def addNode(self, chave: str, entregador: dict):
        atual = self.root
        restante = chave

        while restante:
            primeira_letra = restante[0]
            filho = atual.filhos.get(primeira_letra)

            if filho is None:
                novo_no = Node(rotulo=restante)
                novo_no.valores.append(entregador)
                atual.filhos[primeira_letra] = novo_no
                self.total_nos += 1
                return

            l = self.longest_prefix(restante, filho.rotulo)

            if l == len(filho.rotulo):
                restante = restante[l:]
                atual = filho
                if not restante:
                    atual.valores.append(entregador)
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
                    nova_folha.valores.append(entregador)
                    no_intermediario.filhos[sufixo_restante[0]] = nova_folha
                    self.total_nos += 2
                else:
                    no_intermediario.valores.append(entregador)
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