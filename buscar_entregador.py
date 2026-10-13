import numpy as np
import pandas as pd

class Node:
    def __init__(self, rotulo=""):
        self.rotulo = rotulo
        self.filhos = {} 
        self.valores = [] #somente para folhas
class Trie:
    def __init__(self):
        self.root = Node(rotulo="")
        self.total_nos = 1
    
    def longest_prefix(self, s1: str, s2: str) -> int:
        comum = 0
        limite = min(len(s1), len(s2))

        for i in range(limite):
            if s1[i] != s2[i]:
                break
            comum += 1

        return comum

    def addNode(self, node: str, entregador: dict):
        atual = self.root
        restante = node 

        while restante:
            begin = restante[0]
            filho = atual.filhos.get(begin)
            
            # não possui filho
            if filho is None:
                novo_node = Node(rotulo = restante)
                novo_node.valores.append(entregador)
                atual.filhos[begin] = novo_node # linkagem entre pai (atual) e filho(novo_node)
                self.total_nos+=1
                return
            
            # possui filho
            l = self.longest_prefix(restante, filho.rotulo)
            
            if l == len(filho.rotulo):
                restante = restante[l:]
                atual = filho
                if restante == "": 
                    filho.valores.append(entregador)
                    return
            else:
                # caso que é igual até certa parte, então divide em dois nós
                novo_node = Node(rotulo = filho.rotulo[:l])
                filho.rotulo = filho.rotulo[l:]
                # conecta filho com novo_node onde chave é novo primeiro caractere dele
                novo_node.filhos[filho.rotulo[0]] = filho
                
                folha = Node(rotulo = restante[l:])
                folha.valores.append(entregador)
                novo_node.filhos[folha.rotulo[l:]] = folha
                
                atual.filhos[begin] = novo_node
                self.total_nos+=2
                return

    def imprimir(self, node=None, nivel=0):
        if node is None:
            node = self.root

        print(
            "  " * nivel
            + f"rótulo={node.rotulo!r}, "
            + f"entregadores={len(node.valores)}"
        )

        for filho in node.filhos.values():
            self.imprimir(filho, nivel + 1)

    def searchNode(self, node: str) -> list:
        if not node:
            return []
        
        atual = self.root
        restante = node
        
        while True:
            filho_match = atual.filhos.get(restante[0])
           
            # se nenhum filho corresponde ao inicio da chave, o caminho nao existe
            if not filho_match:
                return []
            
            l = self.longest_prefix(restante, filho_match.rotulo)
            # rotulo do filho corresponde completamente ao restante da chave, então continue descendo na árvore
            if l == len(filho_match.rotulo):
                restante = restante[l:]
                atual = filho_match
                if restante == "":
                    return atual.valores
            # divergiu em algum momento, então não existe caminho
            else:
                return []
    def coletar(self, node: Node) -> list:
        resultado = []
        pilha = [node]

        while pilha:
            n = pilha.pop()
            resultado.extend(n.valores)
            pilha.extend(n.filhos.values())

        return resultado
            
t = Trie()
t.addNode("abcd1", {"id": 1})
t.addNode("abcd2", {"id": 2})
t.addNode("abx00", {"id": 3})
t.addNode("abx00", {"id": 4})   # mesma chave: folha com 2 entregadores
t.imprimir()
print(t.total_nos)  # esperado: 7
