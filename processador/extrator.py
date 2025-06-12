import pdfplumber
import re
import os
import pandas as pd
from .nome_utils import carregar_dados_validos, extrair_nomes_cpfs_intervalo
from . import db

# Compila expressões regulares apenas uma vez para reutilizar no processamento
RE_VOLTA_TOPO = re.compile(r"Voltar ao topo|Página", re.IGNORECASE)
RE_ATO_COMPLETO = re.compile(
    r"^(PORTARIA|DECRETO|ATO|RESOLUÇÃO|CONTRATO|EXTRATO|EDITAL)\s+N[º°]?\s*([\s\d\w\-/.,]*)",
    re.IGNORECASE,
)
RE_ATO_SIMPLES = re.compile(
    r"^(PORTARIA|DECRETO|ATO|RESOLUÇÃO|CONTRATO|EXTRATO|EDITAL)\b",
    re.IGNORECASE,
)

# Padrões de ruídos removidos do texto
RE_PADROES_RUIDOS = [
    re.compile(r"Cilindro Zero", re.IGNORECASE),
    re.compile(r"Papel Guilhotina Um", re.IGNORECASE),
    re.compile(r"www\.imprensaoficial\.rr\.gov\.br\s*Sumário", re.IGNORECASE),
    re.compile(r"\b1944\b", re.IGNORECASE),
]
RE_ADIEOMLRO = re.compile(r"Adieomlro.*?meoo sass\s*,", re.DOTALL | re.IGNORECASE)


diretorio_base = os.path.dirname(os.path.dirname(__file__))
caminho_csv = os.path.join(diretorio_base, "servidores_cpf_randomicos.csv")
dados_validos = carregar_dados_validos(caminho_csv)
if not isinstance(dados_validos, dict):
    raise ValueError("Erro: dados_validos não é um dicionário!")
else:
    print("Dados válidos carregados com sucesso.")


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
    for regex in RE_PADROES_RUIDOS:
        texto = regex.sub("", texto)
    texto = RE_ADIEOMLRO.sub("", texto)
    texto = re.sub(r"\n+", "\n", texto)
    texto = re.sub(r"[ ]{2,}", " ", texto)
    return texto.strip()

def extrair_atos_dinamicamente(df, dados_validos, info_fonte, ano_documento, caminho_pdf):
    """
    Extrai atos de forma dinâmica a partir do DataFrame.
    Detecta o início de um novo ato quando uma linha (sem indentação) inicia com
    palavras-chave como PORTARIA, DECRETO, ATO, RESOLUÇÃO, CONTRATO, EXTRATO ou EDITAL.
    Acumula as linhas do ato até o próximo cabeçalho, limpa ruídos, extrai nomes/CPFs
    e retorna uma lista de dicionários com as informações do ato.
    """
    atos = []
    ato_atual = None
    prev_line_number = None

    for line_number, linha_text in df.itertuples(index=False, name=None):
        linha_text = linha_text.strip()

        # Ignora linhas de ruído, como paginação ou "Voltar ao topo"
        if RE_VOLTA_TOPO.search(linha_text):
            continue

        # Se a linha inicia com um cabeçalho (sem indentação)
        if RE_ATO_SIMPLES.match(linha_text) and linha_text == linha_text.lstrip():
            if ato_atual is not None:
                ato_atual["linha_final"] = prev_line_number if prev_line_number is not None else line_number
                texto_ato = "\n".join(ato_atual["linhas"])
                texto_ato = limpar_ruidos(texto_ato)
                df_slice = df.iloc[ato_atual["linha_inicio"] - 1 : ato_atual["linha_final"]]
                nomes_cpfs = extrair_nomes_cpfs_intervalo(df_slice, dados_validos=dados_validos)
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
            match = RE_ATO_COMPLETO.match(linha_text)
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
        df_slice = df.iloc[ato_atual["linha_inicio"] - 1 : ato_atual["linha_final"]]
        nomes_cpfs = extrair_nomes_cpfs_intervalo(df_slice, dados_validos=dados_validos)
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


def processar_pdfs_em_diretorio(diretorio):
    """Processa todos os PDFs no diretório."""
    for raiz, _, arquivos in os.walk(diretorio):
        for arquivo in arquivos:
            if arquivo.lower().endswith('.pdf'):
                caminho_pdf = os.path.join(raiz, arquivo)
                if db.arquivo_ja_processado(caminho_pdf):
                    print(f"Arquivo já processado: {caminho_pdf}")
                    continue
                print(f"Processando: {caminho_pdf}")
                with pdfplumber.open(caminho_pdf) as pdf:
                    texto_completo = "\n".join([pagina.extract_text() or "" for pagina in pdf.pages])
                df = carregar_pdf_em_dataframe(texto_completo)
                ano_documento = extrair_ano_documento(texto_completo)
                info_fonte = extrair_info_fonte(texto_completo)
                atos = extrair_atos_dinamicamente(df, dados_validos, info_fonte, ano_documento, caminho_pdf)
                db.salvar_atos_no_mongodb(atos)
                db.registrar_arquivo_processado(caminho_pdf)

def main():
    """Ponto de entrada principal para processamento dos PDFs."""
    diretorio_pdfs = os.path.join(diretorio_base, "scrapydoe", "spiders", "pdfs")
    processar_pdfs_em_diretorio(diretorio_pdfs)


if __name__ == "__main__":
    main()
