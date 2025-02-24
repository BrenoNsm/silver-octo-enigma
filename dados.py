import re
import requests
import pdfplumber
import pandas as pd
import openpyxl
import os

# Criar arquivo Excel no início do programa
def criar_arquivo_excel(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        df = pd.DataFrame(columns=["Nome", "CPF", "Matrícula", "Orgão", "Cargo"])
        df.to_excel(caminho_arquivo, index=False, engine="openpyxl")
        print(f"[INFO] Arquivo {caminho_arquivo} criado.", flush=True)

# Função para extrair texto do PDF
def extrair_texto_pdf(caminho_pdf):
    texto_completo = ""
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_completo += pagina.extract_text() + "\n"
    return texto_completo

# Função para encontrar CPFs no texto
def encontrar_cpfs(texto):
    padrao_cpf = r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b'
    cpfs = re.findall(padrao_cpf, texto)
    cpfs_unicos = list(set([re.sub(r'\D', '', cpf) for cpf in cpfs]))  # Remove duplicatas e formata
    return cpfs_unicos

# Função para buscar informações na API
def consultar_api_transparencia(cpf):
    url = f"https://api.transparencia.rr.gov.br/api/v1/portal/transparencia/pesquisar-remuneracoes?cpf={cpf}&size=1&page=0"
    resposta = requests.get(url)
    
    if resposta.status_code == 200:
        dados = resposta.json()
        if "data" in dados and "content" in dados["data"] and len(dados["data"]["content"]) > 0:
            conteudo = dados["data"]["content"][0]
            nome = conteudo.get("nome", "Não encontrado")
            matricula = conteudo.get("matricula", "Não encontrado")
            orgao = conteudo.get("orgao", "Não encontrado")
            cargo = conteudo.get("cargo", "Não encontrado")
            return nome, matricula, orgao, cargo
    return "Não encontrado", "Não encontrado", "Não encontrado", "Não encontrado"

# Função para verificar se CPF já está no arquivo Excel
def cpf_ja_registrado(cpf, caminho_arquivo):
    try:
        df_existente = pd.read_excel(caminho_arquivo, engine="openpyxl")
        return cpf in df_existente["CPF"].astype(str).values
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[ERRO] Não foi possível verificar a planilha: {e}", flush=True)
        return False

# Função para processar todos os PDFs dentro do diretório
def processar_diretorio(caminho_diretorio, caminho_excel):
    criar_arquivo_excel(caminho_excel)
    for ano in sorted(os.listdir(caminho_diretorio)):
        caminho_ano = os.path.join(caminho_diretorio, ano)
        if os.path.isdir(caminho_ano):
            print(f"[INFO] Processando arquivos do ano {ano}...", flush=True)
            for arquivo in os.listdir(caminho_ano):
                if arquivo.lower().endswith(".pdf"):
                    caminho_pdf = os.path.join(caminho_ano, arquivo)
                    print(f"[INFO] Processando {caminho_pdf}...", flush=True)
                    processar_pdf(caminho_pdf, caminho_excel)

# Função principal
def processar_pdf(caminho_pdf, caminho_excel):
    print("[INFO] Extraindo texto do PDF...", flush=True)
    texto = extrair_texto_pdf(caminho_pdf)
    
    print("[INFO] Identificando CPFs no texto...", flush=True)
    cpfs = encontrar_cpfs(texto)
    
    for cpf in cpfs:
        if cpf_ja_registrado(cpf, caminho_excel):
            print(f"[INFO] CPF {cpf} já está registrado. Pulando consulta.", flush=True)
            continue
        
        print(f"[INFO] Consultando API para CPF: {cpf}...", flush=True)
        nome, matricula, orgao, cargo = consultar_api_transparencia(cpf)
        print(f"[INFO] Dados encontrados: Nome: {nome}, CPF: {cpf}, Matrícula: {matricula}, Orgão: {orgao}, Cargo: {cargo}", flush=True)
        
        if nome != "Não encontrado":
            df_existente = pd.read_excel(caminho_excel, engine="openpyxl")
            novo_registro = pd.DataFrame([{ "Nome": nome, "CPF": cpf, "Matrícula": matricula, "Orgão": orgao, "Cargo": cargo }])
            df_final = pd.concat([df_existente, novo_registro], ignore_index=True)
            df_final.to_excel(caminho_excel, index=False, engine="openpyxl")
            print(f"[INFO] Registro inserido para CPF {cpf} em {caminho_excel}", flush=True)
    
# Executar
caminho_diretorio = "/home/ubuntu/rede_complexa/Atos/silver-octo-enigma/scrapydoe/spiders/pdfs"  # Altere para o caminho do diretório
caminho_excel = "dados_servidores_executivo.xlsx"
processar_diretorio(caminho_diretorio, caminho_excel)
