from pymongo import MongoClient
import networkx as nx
import matplotlib.pyplot as plt

# Conectar ao MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["atos"]
collection = db["documentos"]

# Recuperar os dados
documentos = list(collection.find({}, {"Identificador do Ato": 1, "pessoas": 1}))

# Criar o grafo
grafo = nx.Graph()

# Dicionário para controlar duplicatas de CPFs
cpfs_adicionados = {}

# Construir os nós e arestas
for documento in documentos:
    identificador_ato = documento.get("Identificador do Ato")
    pessoas = documento.get("pessoas", [])

    # Adicionar o identificador do ato como nó central
    grafo.add_node(identificador_ato, tipo="ato")

    # Conectar o ato às pessoas (garantindo que não haja duplicatas de CPF)
    for pessoa in pessoas:
        nome_pessoa = pessoa["nome"]
        cpf_pessoa = pessoa["cpf"]

        # Verificar se o CPF já foi adicionado
        if cpf_pessoa not in cpfs_adicionados:
            grafo.add_node(nome_pessoa, tipo="pessoa")  # Adicionar pessoa como nó
            cpfs_adicionados[cpf_pessoa] = nome_pessoa  # Marcar CPF como processado

        # Adicionar aresta entre o ato e a pessoa
        grafo.add_edge(identificador_ato, cpfs_adicionados[cpf_pessoa])

# Configurar a visualização
plt.figure(figsize=(50, 50))  # Tamanho da imagem ajustado para grandes redes

# Usar spring layout para distribuição
pos = nx.spring_layout(grafo, seed=42, k=1.5 / (len(grafo.nodes) ** 0.5))  # Ajustar espaçamento

# Diferenciar nós por tipo
nodos_ato = [n for n, attr in grafo.nodes(data=True) if attr["tipo"] == "ato"]
nodos_pessoa = [n for n, attr in grafo.nodes(data=True) if attr["tipo"] == "pessoa"]

# Desenhar nós dos atos (centrais)
nx.draw_networkx_nodes(grafo, pos, nodelist=nodos_ato, node_size=2000, node_color="red", label="Atos")
# Desenhar nós das pessoas
nx.draw_networkx_nodes(grafo, pos, nodelist=nodos_pessoa, node_size=1000, node_color="lightblue", label="Pessoas")
# Desenhar arestas
nx.draw_networkx_edges(grafo, pos, edge_color="gray")
# Adicionar rótulos
nx.draw_networkx_labels(grafo, pos, font_size=10, font_color="black")

# Título e legenda
plt.title("Rede Complexa de Pessoas por Ato", fontsize=24)
plt.legend(scatterpoints=1, fontsize=16, loc="upper right")

# Salvar o gráfico como arquivo
plt.savefig("rede_pessoas_ato_sem_duplicatas.png", dpi=300, bbox_inches="tight")  # Alta resolução e tamanho ajustado
plt.close()
