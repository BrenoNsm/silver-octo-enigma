from flask import Flask, Response, render_template, request, jsonify
from pymongo import MongoClient
import networkx as nx
from io import BytesIO

# Configuração do Flask
app = Flask(__name__)

# Configuração do MongoDB
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "atos2"
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
            print(f"Buscando pessoa: {person} com CPF: {cpf}")


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
    level = int(request.args.get("level", 1))  # Nível padrão é 1
    if not query:
        return "Consulta não pode estar vazia.", 400

    query_normalized = query.replace(".", "").replace("-", "")

    # Busca inicial – nível 1
    documentos_cursor = collection.find({
        "$or": [
            {"pessoas.nome": {"$regex": query, "$options": "i"}},
            {"pessoas.cpf": query_normalized},
            {"Identificador do Ato": {"$regex": query, "$options": "i"}}
        ]
    })
    documentos = list(documentos_cursor)

    # Se o usuário escolheu relatório de nível 2, expande a busca
    if level > 1:
        additional_documentos = []
        persons = set()
        # Extrai todos os nomes (e cpf, se disponíveis) dos documentos iniciais
        for doc in documentos:
            for p in doc.get("pessoas", []):
                nome = p.get("nome")
                cpf = p.get("cpf")
                if nome and cpf:
                    persons.add(f"{nome} ({cpf})")
                elif nome:
                    persons.add(nome)
                elif cpf:
                    persons.add(cpf)
        # Para cada pessoa encontrada, faça uma nova busca (como “contato”)
        for person in persons:
            cpf = None
            name = person
            if "(" in person and ")" in person:
                # Extrai o nome e o cpf, se estiver no formato "nome (cpf)"
                name = person.split(" (")[0]
                cpf = person.split(" (")[1].replace(")", "")
            query_person = {"$or": []}
            if name:
                query_person["$or"].append({"pessoas.nome": {"$regex": name, "$options": "i"}})
            if cpf:
                query_person["$or"].append({"pessoas.cpf": cpf})
            if query_person["$or"]:
                additional_cursor = collection.find(query_person)
                additional_documentos.extend(list(additional_cursor))
        # Adiciona os documentos adicionais, evitando duplicatas (usando o _id)
        documentos_ids = {str(doc['_id']) for doc in documentos}
        for doc in additional_documentos:
            if str(doc['_id']) not in documentos_ids:
                documentos.append(doc)
                documentos_ids.add(str(doc['_id']))

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
            cpf = p.get("cpf", "CPF não disponível")
            label = f"{nome} ({cpf})" if nome and cpf else nome or cpf

            if nome != pessoa_principal.get("nome"):
                connection_count[label] = connection_count.get(label, 0) + 1
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
        query=query,
        level=level,
        header=header,
        ranking=ranking,
        acts_by_person=acts_by_person,
        degree_ranking=degree_ranking,
        betweenness_ranking=betweenness_ranking
    )


@app.route("/suggest", methods=["GET"])
def suggest():
    q = request.args.get("q", "")
    if not q:
        return jsonify(suggestions=[])
    
    pipeline = [
        {"$unwind": "$pessoas"},
        {"$match": {"pessoas.nome": {"$regex": q, "$options": "i"}}},
        {"$group": {"_id": "$pessoas.nome"}},
        {"$sort": {"_id": 1}},
        {"$limit": 10}  # Limita o número de sugestões (opcional)
    ]
    results = list(collection.aggregate(pipeline))
    suggestions = [result["_id"] for result in results if result["_id"]]
    return jsonify(suggestions=suggestions)


# Executa o servidor Flask
#if __name__ == "__main__":
#    app.run(debug=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

