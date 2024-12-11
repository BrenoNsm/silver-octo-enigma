import networkx as nx
import matplotlib.pyplot as plt

def gerar_grafo_atos(atos):
    """
    Gera um grafo a partir de uma lista de atos.

    Parâmetro:
    - atos (list): Lista de dicionários contendo os dados dos atos, órgãos emissores e pessoas envolvidas.

    Retorna:
    - G (networkx.Graph): Grafo com nós representando atos, pessoas e órgãos emissores, e arestas entre eles.
    """
    G = nx.Graph()

    for ato in atos:
        ato_id = ato['Identificador do Ato']
        #orgao = ato['Órgão Emissor do Ato']

        # Adiciona o nó para o órgão emissor, se ainda não existir
        #G.add_node(orgao, tipo='órgão')

        # Adiciona o nó do ato
        G.add_node(ato_id, tipo=ato['Tipo do Ato'])

        # Cria aresta entre o órgão emissor e o ato
        #G.add_edge(orgao, ato_id)

        # Para cada pessoa, adiciona nó e cria aresta com o ato correspondente
        for nome, (cpf, linha) in ato['Nomes e CPFs'].items():
            G.add_node(nome, tipo='pessoa', cpf=cpf)
            G.add_edge(ato_id, nome)

    return G

# Exemplo de uso
atos_exemplo = [
    {
        'Identificador do Ato': 'Nº 1311-P',
        'Órgão Emissor do Ato': 'Governo do Estado de Roraima',
        'Nomes e CPFs': {'PATRICIA CARLA DA SILVA': ('94802262', 147)}
    },
    {
        'Identificador do Ato': 'Nº 1325-P',
        'Órgão Emissor do Ato': 'Governo do Estado de Roraima',
        'Nomes e CPFs': {
            'NAIARA OLIVEIRA ALVES': ('4269002271', 163),
            'RISOLETA MESSIAS DE SOUZA': ('76238261234', 164)
        }
    },
    {
        'Identificador do Ato': 'Nº 1326-P',
        'Órgão Emissor do Ato': 'Governo do Estado de Roraima',
        'Nomes e CPFs': {'JESSIKA DE SOUZA ALBARADO': ('3182199218', 182)}
    }
]

def exportar_para_graphml(grafo, nome_arquivo="grafo_gephi.graphml"):
    """
    Exporta um grafo NetworkX para um arquivo GraphML compatível com Gephi.

    Parâmetros:
    - grafo: Grafo criado com NetworkX.
    - nome_arquivo: Nome do arquivo GraphML a ser gerado.
    """
    try:
        nx.write_graphml(grafo, nome_arquivo)
        print(f"Grafo exportado com sucesso para '{nome_arquivo}'")
    except Exception as e:
        print(f"Erro ao exportar o grafo: {e}")
