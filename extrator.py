import pdfplumber
import re
import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from extrator_nomes_csv import carregar_dados_validos, extrair_nomes_cpfs_intervalo

# Conexão com MongoDB
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)

# Banco e coleções
DB_ATOS = client["atos1"]
COL_ATOS = DB_ATOS["documentos"]
DB_ARQUIVOS = client["arquivos_processados"]
COL_ARQUIVOS = DB_ARQUIVOS["arquivos"]

# Caminho do CSV com os dados válidos
caminho_csv = "servidores_cpf_randomicos.csv"
dados_validos = carregar_dados_validos(caminho_csv)
if not isinstance(dados_validos, dict):
    raise ValueError("Erro: dados_validos não é um dicionário!")
else:
    print('Dados válidos carregados com sucesso.')

meses_portugues = {
    "janeiro": "01", "fevereiro": "02", "março": "03",
    "abril": "04", "maio": "05", "junho": "06",
    "julho": "07", "agosto": "08", "setembro": "09",
    "outubro": "10", "novembro": "11", "dezembro": "12"
}

def normalizar_data(data):
    data = data.lower().replace('é', 'e')
    partes = data.strip().split(" de ")
    if len(partes) == 3:
        dia, mes, ano = partes[0].zfill(2), meses_portugues.get(partes[1]), partes[2]
        return f"{dia}/{mes}/{ano}" if mes else None
    return None

def arquivo_ja_processado(nome_arquivo):
    """ Verifica no MongoDB se o arquivo já foi processado. """
    return COL_ARQUIVOS.find_one({"arquivo": nome_arquivo}) is not None

def registrar_arquivo_processado(nome_arquivo):
    """ Registra o arquivo processado no MongoDB. """
    COL_ARQUIVOS.insert_one({"arquivo": nome_arquivo, "data_processamento": datetime.now()})
    print(f"Arquivo registrado no MongoDB: {nome_arquivo}")

def carregar_pdf_em_dataframe(texto):
    """ Carrega o texto do PDF em um DataFrame. """
    linhas = texto.splitlines()
    return pd.DataFrame([{"Line Number": i + 1, "Text": line} for i, line in enumerate(linhas)])

def salvar_atos_no_mongodb(atos):
    """ Salva os atos extraídos no MongoDB. """
    if atos:
        COL_ATOS.insert_many(atos)
        print(f"{len(atos)} documentos inseridos no MongoDB.")

def processar_pdfs_em_diretorio(diretorio):
    """ Processa todos os PDFs no diretório. """
    for raiz, _, arquivos in os.walk(diretorio):
        ano_documento = os.path.basename(raiz)
        if not ano_documento.isdigit():
            continue
        for arquivo in arquivos:
            if arquivo.lower().endswith('.pdf'):
                caminho_pdf = os.path.join(raiz, arquivo)
                if arquivo_ja_processado(caminho_pdf):
                    print(f"Arquivo já processado: {caminho_pdf}")
                    continue
                print(f"Processando: {caminho_pdf}")
                with pdfplumber.open(caminho_pdf) as pdf:
                    texto_completo = "".join([pagina.extract_text() or "" for pagina in pdf.pages])
                df = carregar_pdf_em_dataframe(texto_completo)
                atos = extrair_todos_atos(df, {}, dados_validos, ano_documento, caminho_pdf)
                salvar_atos_no_mongodb(atos)
                registrar_arquivo_processado(caminho_pdf)

def extrair_todos_atos(df, info_fonte, dados_validos, ano_documento, caminho_pdf):
    """ Extrai atos do DataFrame. """
    padrao_ato_principal = re.compile(r"^(PORTARIA|DECRETO|ATO|RESOLUÇÃO|CONTRATO|EXTRATO|EDITAL)\s+N[º°]?([\s\d\w\-/.,]*)", re.IGNORECASE)
    atos = []
    for _, row in df.iterrows():
        texto_linha = row["Text"]
        linha_numero = row["Line Number"]
        match = padrao_ato_principal.match(texto_linha)
        if match:
            tipo = match.group(1).capitalize()
            identificador = f"{tipo} {match.group(2).strip()}"
            linha_inicio = linha_numero
            linha_final = linha_numero + 15
            if linha_final > df["Line Number"].iloc[-1]:
                linha_final = df["Line Number"].iloc[-1]
            nomes_cpfs = extrair_nomes_cpfs_intervalo(df, linha_inicio, linha_final, dados_validos)
            pessoas = [{"nome": nome, "cpf": cpf} for nome, (cpf, _) in nomes_cpfs.items()]
            texto_ato = "\n".join(df.loc[df["Line Number"].between(linha_inicio, linha_final), "Text"])
            atos.append({
                **info_fonte,
                "Tipo do Ato": tipo,
                "Identificador do Ato": identificador,
                "Data do Ato": None,
                "Ano Documento": ano_documento,
                "Texto do Ato": texto_ato,
                "Diretório do Arquivo": caminho_pdf,
                "pessoas": pessoas
            })
    return atos

# Caminho para os PDFs
diretorio_pdfs = r"scrapydoe/spiders/pdfs"
processar_pdfs_em_diretorio(diretorio_pdfs)
