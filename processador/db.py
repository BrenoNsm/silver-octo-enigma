from datetime import datetime
from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)

DB_ATOS = client["atos2"]
COL_ATOS = DB_ATOS["documentos"]
DB_ARQUIVOS = client["arquivos_processados2"]
COL_ARQUIVOS = DB_ARQUIVOS["arquivos"]


def arquivo_ja_processado(nome_arquivo):
    """Verifica se o arquivo já foi processado."""
    return COL_ARQUIVOS.find_one({"arquivo": nome_arquivo}) is not None


def registrar_arquivo_processado(nome_arquivo):
    """Registra o arquivo processado."""
    COL_ARQUIVOS.insert_one({"arquivo": nome_arquivo, "data_processamento": datetime.now()})


def salvar_atos_no_mongodb(atos):
    """Insere os atos extraídos no MongoDB."""
    if atos:
        COL_ATOS.insert_many(atos)
        print(f"{len(atos)} documentos inseridos no MongoDB.")
