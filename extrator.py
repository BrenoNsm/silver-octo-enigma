import pdfplumber
import re
import os
import pandas as pd
import csv
from pymongo import MongoClient
from datetime import datetime
from extrator_nomes_csv import carregar_dados_validos, extrair_nomes_cpfs_intervalo

# Caminho do CSV com os dados válidos
caminho_csv = "servidores_cpf_randomicos.csv"
dados_validos = carregar_dados_validos(caminho_csv)
if not isinstance(dados_validos, dict):
    raise ValueError("Erro: dados_validos não é um dicionário!")
else:
    print('Dados válidos carregados com sucesso.')

# Mapeamento de meses em português para números
meses_portugues = {
    "janeiro": "01", "fevereiro": "02", "março": "03",
    "abril": "04", "maio": "05", "junho": "06",
    "julho": "07", "agosto": "08", "setembro": "09",
    "outubro": "10", "novembro": "11", "dezembro": "12"
}

def normalizar_data(data):
    """ Normaliza datas no formato 'XX de mês de XXXX' para 'DD/MM/YYYY'. """
    data = data.lower().replace('é', 'e')
    dias_semana = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    for dia in dias_semana:
        data = data.replace(dia + ', ', '').replace(dia, '')
    partes = data.strip().split(" de ")
    if len(partes) == 3:
        dia, mes, ano = partes[0].zfill(2), meses_portugues.get(partes[1]), partes[2]
        return f"{dia}/{mes}/{ano}" if mes else None
    return None

def verificar_e_inicializar_controle(caminho_controle):
    """ Verifica se o arquivo de controle existe, e o inicializa se necessário. """
    try:
        if not os.path.exists(caminho_controle):
            with open(caminho_controle, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Arquivo", "Data de Processamento"])
            print(f"Arquivo de controle criado: {caminho_controle}")
        with open(caminho_controle, mode='r', newline='', encoding='utf-8') as file:
            leitor = csv.reader(file)
            next(leitor, None)  # Pular cabeçalho
            return [linha[0] for linha in leitor if linha]
    except Exception as e:
        print(f"Erro ao verificar/inicializar controle: {e}")
        return []

def registrar_arquivo_processado(nome_arquivo, caminho_controle='arquivos_processados.csv'):
    """ Registra o arquivo como processado no arquivo de controle. """
    try:
        with open(caminho_controle, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([nome_arquivo, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        print(f"Arquivo registrado como processado: {nome_arquivo}")
    except Exception as e:
        print(f"Erro ao registrar o arquivo processado: {e}")

def arquivo_ja_processado(nome_arquivo, caminho_controle='arquivos_processados.csv'):
    """ Verifica se o arquivo já foi processado. """
    arquivos_processados = verificar_e_inicializar_controle(caminho_controle)
    return os.path.abspath(nome_arquivo) in map(os.path.abspath, arquivos_processados)

def carregar_pdf_em_dataframe(texto):
    """ Carrega o texto do PDF em um DataFrame para processamento. """
    linhas = texto.splitlines()
    return pd.DataFrame([{"Line Number": i + 1, "Text": line} for i, line in enumerate(linhas)])

def salvar_atos_no_mongodb(atos, uri="mongodb://localhost:27017/", nome_banco="atos1", nome_colecao="documentos"):
    """ Salva os atos extraídos no MongoDB. """
    try:
        client = MongoClient(uri)
        db, colecao = client[nome_banco], client[nome_banco][nome_colecao]
        documentos = []
        for ato in atos:
            ato.pop("Linha Início", None)
            ato.pop("Linha Final", None)
            nomes_cpfs = ato.pop("Nomes e CPFs", {})
            ato["pessoas"] = [{"nome": nome, "cpf": cpf} for nome, (cpf, _) in nomes_cpfs.items()]
            documentos.append(ato)
        colecao.insert_many(documentos)
        print(f"Documentos inseridos com sucesso: {len(documentos)}")
    except Exception as e:
        print(f"Erro ao salvar no MongoDB: {e}")

def processar_pdfs_em_diretorio(diretorio, caminho_controle='arquivos_processados.csv'):
    """ Processa todos os PDFs em um diretório especificado. """
    for raiz, _, arquivos in os.walk(diretorio):
        ano_documento = os.path.basename(raiz)
        if not ano_documento.isdigit():
            continue
        for arquivo in arquivos:
            if arquivo.lower().endswith('.pdf'):
                caminho_pdf = os.path.join(raiz, arquivo)
                if arquivo_ja_processado(caminho_pdf, caminho_controle):
                    print(f"Arquivo já processado: {caminho_pdf}")
                    continue
                print(f"Processando o arquivo: {caminho_pdf}")
                with pdfplumber.open(caminho_pdf) as pdf:
                    texto_completo = ""
                    for pagina in pdf.pages:
                        texto_pagina = pagina.extract_text()
                        if texto_pagina:
                            texto_completo += texto_pagina
                        else:
                            print(f"Falha ao extrair texto da página {pagina.page_number}")
                    df = carregar_pdf_em_dataframe(texto_completo)
                    info_fonte = {}  # Placeholder para informações adicionais da fonte
                    atos = extrair_todos_atos(df, info_fonte, dados_validos, ano_documento, caminho_pdf)
                    salvar_atos_no_mongodb(atos)
                    registrar_arquivo_processado(caminho_pdf, caminho_controle)

def extrair_todos_atos(df, info_fonte, dados_validos, ano_documento, caminho_pdf):
    """ Extrai todos os atos de um DataFrame de texto. """
    padrao_ato_principal = re.compile(
        r"^(PORTARIA|DECRETO|ATO|RESOLUÇÃO|CONTRATO|EXTRATO|EDITAL)\s+N[º°]?([\s\d\w\-/.,]*)",
        re.IGNORECASE
    )
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

            nomes_cpfs = extrair_nomes_cpfs_intervalo(
                df, linha_inicial=linha_inicio, linha_final=linha_final, dados_validos=dados_validos
            )

            texto_ato = "\n".join(df.loc[df["Line Number"].between(linha_inicio, linha_final), "Text"])

            atos.append({
                **info_fonte,
                "Tipo do Ato": tipo,
                "Identificador do Ato": identificador,
                "Data do Ato": None,
                "Ano Documento": ano_documento,
                "Texto do Ato": texto_ato,
                "Linha Início": linha_inicio,
                "Linha Final": linha_final,
                "Nomes e CPFs": nomes_cpfs,
                "Diretório do Arquivo": caminho_pdf,
            })
    return atos

# Caminho para os PDFs
diretorio_pdfs = r"C:\\Users\\bnascimento\\Documents\\silver-octo-enigma\\silver-octo-enigma\\scrapydoe\\spiders\\pdfs"
processar_pdfs_em_diretorio(diretorio_pdfs)