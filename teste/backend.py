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
    return render_template("index.html")

# Rota para buscar dados e retornar a rede completa no formato Gephi
@app.route("/download_full_network", methods=["GET"])
def download_full_network():
    pessoas = collection.find()

    pessoas = list(pessoas)
    if not pessoas:
        return jsonify({"error": "Nenhum dado encontrado para exportar."}), 404

    # Construir o grafo usando NetworkX
    graph = nx.Graph()

    nodes_set = set()
    person_to_acts = {}

    for pessoa in pessoas:
        ato_id = pessoa.get("Identificador do Ato", "Ato Desconhecido")
        if ato_id not in nodes_set:
            graph.add_node(ato_id, label=ato_id, type="Ato")
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
            graph.add_node(person, label=person, type="Pessoa")
            nodes_set.add(person)
        for act in acts:
            graph.add_edge(person, act)

    # Exportar o grafo para o formato GEXF
    gexf_output = BytesIO()
    nx.write_gexf(graph, gexf_output)
    gexf_output.seek(0)

    # Retornar o arquivo para download
    return Response(
        gexf_output,
        mimetype="application/xml",
        headers={"Content-Disposition": "attachment;filename=rede_completa.gexf"}
    )

# Rota para buscar dados no banco de dados e gerar o grafo
@app.route("/search", methods=["POST"])
def search():
    query = request.form.get("query")
    if not query:
        return jsonify({"error": "A consulta não pode estar vazia."}), 400

    # Normalizar CPF (remover pontuação, caso necessário)
    query_normalized = query.replace(".", "").replace("-", "")

    # Pesquisa no banco de dados
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

    # Formatar os dados para o grafo
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

    # Adicionar nós e consolidar conexões
    for person, acts in person_to_acts.items():
        if person not in nodes_set:
            nodes.append({"id": person, "label": person, "type": "Pessoa"})
            nodes_set.add(person)
        for act in acts:
            links.append({"source": act, "target": person})

    return jsonify({"graph_data": {"nodes": nodes, "links": links}})

@app.route("/report")
def report():
    query = request.args.get("query")
    if not query:
        return "Consulta não pode estar vazia.", 400

    query_normalized = query.replace(".", "").replace("-", "")

    pessoas = collection.find({
        "$or": [
            {"pessoas.nome": {"$regex": query, "$options": "i"}},
            {"pessoas.cpf": query_normalized},
            {"Identificador do Ato": {"$regex": query, "$options": "i"}}
        ]
    })

    pessoas = list(pessoas)
    if not pessoas:
        return "Nenhum dado encontrado para gerar o relatório.", 404

    # Construir o cabeçalho do relatório
    pessoa_principal = None
    for pessoa in pessoas:
        for p in pessoa.get("pessoas", []):
            if query.lower() in (p.get("nome", "").lower() or "") or query_normalized == p.get("cpf", ""):
                pessoa_principal = p
                break
        if pessoa_principal:
            break

    if not pessoa_principal:
        return "Nenhum dado encontrado para o CPF ou nome consultado.", 404

    header = f"{pessoa_principal.get('nome', 'Desconhecido')} ({pessoa_principal.get('cpf', 'CPF não disponível')})"

    # Construir o ranking de conexões
    connection_count = {}
    for pessoa in pessoas:
        for p in pessoa.get("pessoas", []):
            nome = p.get("nome", "Desconhecido")
            if nome != pessoa_principal.get("nome"):
                connection_count[nome] = connection_count.get(nome, 0) + 1

    ranking = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)

    # Renderizar o HTML com os dados do relatório
    return render_template("report.html", header=header, ranking=ranking)


# Executa o servidor Flask
if __name__ == "__main__":
    app.run(debug=True)
