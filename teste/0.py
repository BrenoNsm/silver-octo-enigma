from flask import Flask, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)  # Permitir requisições cross-origin

@app.route('/')
def home():
    # Renderiza o template index.html
    return render_template('index.html')

@app.route('/get_network_data')
def get_network_data():
    # Conexão com MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["atos"]
    collection = db["documentos"]
    
    # Recuperar documentos
    documentos = list(collection.find({}, {
        "Identificador do Ato": 1, 
        "Tipo do Ato": 1,
        "Número da Edição": 1,
        "pessoas": 1
    }))
    
    # Converter ObjectId para string
    for doc in documentos:
        doc['_id'] = str(doc['_id'])
    
    return jsonify(documentos)

@app.route('/get_person_data/<nome>')
def get_person_data(nome):
    # Conexão com MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    db = client["atos"]
    collection = db["documentos"]

    pessoa = {
        "nome": nome,
        "cpf": None,
        "atos": [],
        "relacionados": {}
    }

    documentos = collection.find({"pessoas.nome": nome})
    for doc in documentos:
        pessoa["atos"].append(doc["Identificador do Ato"])
        pessoa["cpf"] = next((p["cpf"] for p in doc["pessoas"] if p["nome"] == nome), pessoa["cpf"])
        for pessoa_doc in doc["pessoas"]:
            if pessoa_doc["nome"] != nome:
                if pessoa_doc["nome"] in pessoa["relacionados"]:
                    pessoa["relacionados"][pessoa_doc["nome"]] += 1
                else:
                    pessoa["relacionados"][pessoa_doc["nome"]] = 1

    pessoa["relacionados"] = [{"nome": nome, "frequencia": freq} for nome, freq in pessoa["relacionados"].items()]

    return jsonify(pessoa)

@app.route('/get_act_data/<identificador>')
def get_act_data(identificador):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["atos"]
    collection = db["documentos"]

    ato = collection.find_one({"Identificador do Ato": identificador}, {
        "Identificador do Ato": 1,
        "Ano Documento": 1,
        "Tipo do Ato": 1,
        "Texto do Ato": 1,
        "pessoas.nome": 1
    })

    if ato:
        ato["_id"] = str(ato["_id"])
        ato["pessoas"] = ato.get("pessoas", [])
        return jsonify(ato)
    else:
        return jsonify({"error": "Ato não encontrado"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
