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
DB_ATOS = client["atos2"]
COL_ATOS = DB_ATOS["documentos"]
DB_ARQUIVOS = client["arquivos_processados2"]
COL_ARQUIVOS = DB_ARQUIVOS["arquivos"]

# Caminho do CSV com os dados válidos
caminho_csv = "servidores_cpf_randomicos.csv"
dados_validos = carregar_dados_validos(caminho_csv)
if not isinstance(dados_validos, dict):
    raise ValueError("Erro: dados_validos não é um dicionário!")
else:
    print("Dados válidos carregados com sucesso.")

def arquivo_ja_processado(nome_arquivo):
    """Verifica no MongoDB se o arquivo já foi processado."""
    return COL_ARQUIVOS.find_one({"arquivo": nome_arquivo}) is not None

def registrar_arquivo_processado(nome_arquivo):
    """Registra o arquivo processado no MongoDB."""
    COL_ARQUIVOS.insert_one({"arquivo": nome_arquivo, "data_processamento": datetime.now()})
    print(f"Arquivo registrado no MongoDB: {nome_arquivo}")

def carregar_pdf_em_dataframe(texto):
    """Carrega o texto do PDF em um DataFrame, atribuindo número de linha."""
    linhas = texto.splitlines()
    return pd.DataFrame([{"Line Number": i + 1, "Text": linha} for i, linha in enumerate(linhas)])

def extrair_ano_documento(texto):
    """
    Procura um padrão de data no formato "16 de janeiro de 2024" e retorna o ano encontrado.
    """
    padrao = re.compile(r'\b\d{1,2}\s+de\s+[a-zçã]+\s+de\s+(\d{4})\b', re.IGNORECASE)
    match = padrao.search(texto)
    if match:
        return match.group(1)
    return "Ano não encontrado"

def extrair_info_fonte(texto):
    """
    Extrai informações da fonte a partir do texto do documento.
    Se encontrar "Diário Oficial", define a origem como "Diário Oficial do Estado".
    """
    if "diário oficial" in texto.lower():
        return {"origem": "Diário Oficial do Estado"}
    return {"origem": "Fonte não identificada"}

def limpar_ruidos(texto):
    """
    Remove padrões de ruídos indesejados do texto.
    São removidos padrões fixos (ex.: "Cilindro Zero", "Papel Guilhotina Um", etc.)
    e um bloco de texto indesejado que inicia com "Adieomlro" e vai até "meoo sass,".
    """
    padroes = [
        r"Cilindro Zero",
        r"Papel Guilhotina Um",
        r"www\.imprensaoficial\.rr\.gov\.br\s*Sumário",
        r"\b1944\b"
    ]
    for padrao in padroes:
        texto = re.sub(padrao, "", texto, flags=re.IGNORECASE)
    texto = re.sub(r'Adieomlro.*?meoo sass\s*,', '', texto, flags=re.DOTALL|re.IGNORECASE)
    texto = re.sub(r'\n+', "\n", texto)
    texto = re.sub(r'[ ]{2,}', " ", texto)
    return texto.strip()

def extrair_atos_dinamicamente(df, dados_validos, info_fonte, ano_documento, caminho_pdf):
    """
    Extrai atos de forma dinâmica a partir do DataFrame.
    Detecta o início de um novo ato quando uma linha (sem indentação) inicia com
    palavras-chave como PORTARIA, DECRETO, ATO, RESOLUÇÃO, CONTRATO, EXTRATO ou EDITAL.
    Acumula as linhas do ato até o próximo cabeçalho, limpa ruídos, extrai nomes/CPFs
    e retorna uma lista de dicionários com as informações do ato.
    """
    regex_ato = re.compile(
        r"^(PORTARIA|DECRETO|ATO|RESOLUÇÃO|CONTRATO|EXTRATO|EDITAL)\s+N[º°]?\s*([\s\d\w\-/.,]*)",
        re.IGNORECASE
    )
    regex_ato_simples = re.compile(
        r"^(PORTARIA|DECRETO|ATO|RESOLUÇÃO|CONTRATO|EXTRATO|EDITAL)\b",
        re.IGNORECASE
    )
    
    atos = []
    ato_atual = None
    prev_line_number = None

    for _, row in df.iterrows():
        linha_text = row["Text"].strip()
        line_number = row["Line Number"]

        # Ignora linhas de ruído, como paginação ou "Voltar ao topo"
        if re.search(r"Voltar ao topo|Página", linha_text, re.IGNORECASE):
            continue

        # Se a linha inicia com um cabeçalho (sem indentação)
        if regex_ato_simples.match(linha_text) and linha_text == linha_text.lstrip():
            if ato_atual is not None:
                ato_atual["linha_final"] = prev_line_number if prev_line_number is not None else line_number
                texto_ato = "\n".join(ato_atual["linhas"])
                texto_ato = limpar_ruidos(texto_ato)
                df_slice = df[df["Line Number"].between(ato_atual["linha_inicio"], ato_atual["linha_final"])]
                nomes_cpfs = extrair_nomes_cpfs_intervalo(df_slice, ato_atual["linha_inicio"], ato_atual["linha_final"], dados_validos)
                pessoas = [{"nome": nome, "cpf": cpf} for nome, (cpf, _) in nomes_cpfs.items()]
                ato_atual["Texto do Ato"] = texto_ato
                ato_atual["pessoas"] = pessoas
                ato_atual["Diretório do Arquivo"] = caminho_pdf
                ato_atual["Ano Documento"] = ano_documento
                act_record = {
                    **info_fonte,
                    "Tipo do Ato": ato_atual["Tipo do Ato"],
                    "Identificador do Ato": ato_atual["Identificador do Ato"],
                    "Texto do Ato": ato_atual["Texto do Ato"],
                    "Ano Documento": ato_atual["Ano Documento"],
                    "Diretório do Arquivo": ato_atual["Diretório do Arquivo"],
                    "pessoas": ato_atual["pessoas"]
                }
                atos.append(act_record)
            # Inicia novo ato
            ato_atual = {}
            ato_atual["linhas"] = [linha_text]
            ato_atual["linha_inicio"] = line_number
            ato_atual["linha_final"] = line_number
            match = regex_ato.match(linha_text)
            if match:
                tipo = match.group(1).capitalize()
                identificador = f"{tipo} {match.group(2).strip()}" if match.group(2).strip() != "" else linha_text
            else:
                parts = linha_text.split()
                tipo = parts[0].capitalize() if parts else ""
                identificador = linha_text
            ato_atual["Tipo do Ato"] = tipo
            ato_atual["Identificador do Ato"] = identificador
        else:
            if ato_atual is not None:
                ato_atual["linhas"].append(linha_text)
                ato_atual["linha_final"] = line_number
            else:
                continue
        prev_line_number = line_number

    if ato_atual is not None:
        ato_atual["linha_final"] = ato_atual.get("linha_final", ato_atual["linha_inicio"])
        texto_ato = "\n".join(ato_atual["linhas"])
        texto_ato = limpar_ruidos(texto_ato)
        df_slice = df[df["Line Number"].between(ato_atual["linha_inicio"], ato_atual["linha_final"])]
        nomes_cpfs = extrair_nomes_cpfs_intervalo(df_slice, ato_atual["linha_inicio"], ato_atual["linha_final"], dados_validos)
        pessoas = [{"nome": nome, "cpf": cpf} for nome, (cpf, _) in nomes_cpfs.items()]
        ato_atual["Texto do Ato"] = texto_ato
        ato_atual["pessoas"] = pessoas
        ato_atual["Diretório do Arquivo"] = caminho_pdf
        ato_atual["Ano Documento"] = ano_documento
        act_record = {
            **info_fonte,
            "Tipo do Ato": ato_atual["Tipo do Ato"],
            "Identificador do Ato": ato_atual["Identificador do Ato"],
            "Texto do Ato": ato_atual["Texto do Ato"],
            "Ano Documento": ato_atual["Ano Documento"],
            "Diretório do Arquivo": ato_atual["Diretório do Arquivo"],
            "pessoas": ato_atual["pessoas"]
        }
        atos.append(act_record)
    
    return atos

def salvar_atos_no_mongodb(atos):
    """Salva os atos extraídos no MongoDB."""
    if atos:
        COL_ATOS.insert_many(atos)
        print(f"{len(atos)} documentos inseridos no MongoDB.")

def processar_pdfs_em_diretorio(diretorio):
    """Processa todos os PDFs no diretório."""
    for raiz, _, arquivos in os.walk(diretorio):
        for arquivo in arquivos:
            if arquivo.lower().endswith('.pdf'):
                caminho_pdf = os.path.join(raiz, arquivo)
                if arquivo_ja_processado(caminho_pdf):
                    print(f"Arquivo já processado: {caminho_pdf}")
                    continue
                print(f"Processando: {caminho_pdf}")
                with pdfplumber.open(caminho_pdf) as pdf:
                    texto_completo = "\n".join([pagina.extract_text() or "" for pagina in pdf.pages])
                df = carregar_pdf_em_dataframe(texto_completo)
                ano_documento = extrair_ano_documento(texto_completo)
                info_fonte = extrair_info_fonte(texto_completo)
                atos = extrair_atos_dinamicamente(df, dados_validos, info_fonte, ano_documento, caminho_pdf)
                salvar_atos_no_mongodb(atos)
                registrar_arquivo_processado(caminho_pdf)

# Caminho para os PDFs
diretorio_pdfs = r"scrapydoe/spiders/pdfs"
processar_pdfs_em_diretorio(diretorio_pdfs)
