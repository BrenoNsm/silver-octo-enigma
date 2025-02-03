from flask import Flask, Response, render_template, request, jsonify
from pymongo import MongoClient
import networkx as nx
from io import BytesIO

# Configuração do Flask
app = Flask(__name__)

# Configuração do MongoDB
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "atos1"
COLLECTION_NAME = "documentos"
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Rota para a página inicial
@app.route("/")
def index():
    return render_template("/index.html")

# Rota para buscar dados no banco de dados e gerar o grafo
@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query")
    level = int(request.form.get("level", 1))  # Nível padrão é 1

    if not query:
        return jsonify({"error": "A consulta não pode estar vazia."}), 400

    query_normalized = query.replace(".", "").replace("-", "")

    # Busca inicial no nível 1
    pessoas = collection.find({
        "$or": [
            {"pessoas.nome": {"$regex": query, "$options": "i"}},
            {"pessoas.cpf": query_normalized},
            {"Identificador do Ato": {"$regex": query, "$options": "i"}}
        ]
    })

    pessoas = list(pessoas)
    if not pessoas:
        return jsonify({"error": "Nenhum resultado encontrado."}), 404

    # Montar grafo para o nível
    nodes = []
    links = []
    nodes_set = set()
    person_to_acts = {}

    for pessoa in pessoas:
        ato_id = pessoa.get("Identificador do Ato", "Ato Desconhecido")
        if ato_id not in nodes_set:
            nodes.append({"id": ato_id, "label": ato_id, "type": "Ato"})
            nodes_set.add(ato_id)

        for p in pessoa.get("pessoas", []):
            nome = p.get("nome")
            cpf = p.get("cpf")
            label = f"{nome} ({cpf})" if nome and cpf else nome or cpf

            if label not in person_to_acts:
                person_to_acts[label] = set()
            person_to_acts[label].add(ato_id)

    for person, acts in person_to_acts.items():
        if person not in nodes_set:
            nodes.append({"id": person, "label": person, "type": "Pessoa"})
            nodes_set.add(person)
        for act in acts:
            links.append({"source": act, "target": person})

    # Expandir para nível 2 ou mais
    if level > 1:
        additional_pessoas = []
        for person in person_to_acts.keys():
            cpf = person.split("(")[-1].strip(")") if "(" in person else None
            pessoa_data = collection.find({
                "$or": [
                    {"pessoas.nome": {"$regex": person, "$options": "i"}},
                    {"pessoas.cpf": cpf}
                ]
            })
            additional_pessoas.extend(pessoa_data)

        for pessoa in additional_pessoas:
            ato_id = pessoa.get("Identificador do Ato", "Ato Desconhecido")
            if ato_id not in nodes_set:
                nodes.append({"id": ato_id, "label": ato_id, "type": "Ato"})
                nodes_set.add(ato_id)

            for p in pessoa.get("pessoas", []):
                nome = p.get("nome")
                cpf = p.get("cpf")
                label = f"{nome} ({cpf})" if nome and cpf else nome or cpf

                if label not in nodes_set:
                    nodes.append({"id": label, "label": label, "type": "Pessoa"})
                    nodes_set.add(label)
                links.append({"source": ato_id, "target": label})

    return jsonify({"graph_data": {"nodes": nodes, "links": links}})


@app.route("/report")
def report():
    query = request.args.get("query")
    if not query:
        return "Consulta não pode estar vazia.", 400

    query_normalized = query.replace(".", "").replace("-", "")

    documentos = collection.find({
        "$or": [
            {"pessoas.nome": {"$regex": query, "$options": "i"}},
            {"pessoas.cpf": query_normalized},
            {"Identificador do Ato": {"$regex": query, "$options": "i"}}
        ]
    })

    documentos = list(documentos)
    if not documentos:
        return "Nenhum dado encontrado para gerar o relatório.", 404

    # Identifica a pessoa principal (a partir da consulta)
    pessoa_principal = None
    for doc in documentos:
        for p in doc.get("pessoas", []):
            if query.lower() in (p.get("nome", "").lower() or "") or query_normalized == p.get("cpf", ""):
                pessoa_principal = p
                break
        if pessoa_principal:
            break

    if not pessoa_principal:
        return "Nenhum dado encontrado para o CPF ou nome consultado.", 404

    header = f"{pessoa_principal.get('nome', 'Desconhecido')} ({pessoa_principal.get('cpf', 'CPF não disponível')})"

    # Ranking de conexões simples
    connection_count = {}
    for doc in documentos:
        for p in doc.get("pessoas", []):
            nome = p.get("nome", "Desconhecido")
            if nome != pessoa_principal.get("nome"):
                connection_count[nome] = connection_count.get(nome, 0) + 1
    ranking = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)

    # Agrupa os atos associados a cada pessoa
    acts_by_person = {}
    for doc in documentos:
        identificador = doc.get("Identificador do Ato", "Ato Desconhecido")
        tipo = doc.get("Tipo do Ato", "Tipo não disponível")
        ano = doc.get("Ano Documento", "Ano não disponível")
        texto = doc.get("Texto do Ato", "Texto não disponível")
        for p in doc.get("pessoas", []):
            nome = p.get("nome", "Desconhecido")
            if nome not in acts_by_person:
                acts_by_person[nome] = []
            acts_by_person[nome].append({
                "identificador": identificador,
                "tipo": tipo,
                "ano": ano,
                "texto": texto,
                "arquivo": doc.get("Diretório do Arquivo", "")
            })

    # Cálculo das métricas de centralidade (utilizando NetworkX)
    import networkx as nx
    G = nx.Graph()
    for doc in documentos:
        ato_id = doc.get("Identificador do Ato", "Ato Desconhecido")
        G.add_node(ato_id, type="Ato")
        for p in doc.get("pessoas", []):
            nome = p.get("nome")
            cpf = p.get("cpf")
            person_label = f"{nome} ({cpf})" if nome and cpf else (nome or cpf or "Pessoa Desconhecida")
            G.add_node(person_label, type="Pessoa")
            G.add_edge(ato_id, person_label)

    degree_centrality = nx.degree_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G)

    degree_ranking = []
    betweenness_ranking = []
    for node, data in G.nodes(data=True):
        if data.get("type") == "Pessoa":
            degree_ranking.append((node, degree_centrality.get(node, 0)))
            betweenness_ranking.append((node, betweenness_centrality.get(node, 0)))
    degree_ranking = sorted(degree_ranking, key=lambda x: x[1], reverse=True)
    betweenness_ranking = sorted(betweenness_ranking, key=lambda x: x[1], reverse=True)

    return render_template(
        "report.html",
        header=header,
        ranking=ranking,
        acts_by_person=acts_by_person,
        degree_ranking=degree_ranking,
        betweenness_ranking=betweenness_ranking
    )


# Executa o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)
