import re
from unidecode import unidecode  # Para remover acentos
import pandas as pd
from unidecode import unidecode  # Para remover acentos


def buscar_cpf_por_nome(nome_normalizado, dados_validos):
    """
    Busca o CPF correspondente ao nome normalizado nos dados válidos.
    :param nome_normalizado: Nome normalizado para busca.
    :param dados_validos: Dicionário de nomes normalizados e seus respectivos CPFs.
    :return: CPF correspondente ou None.
    """
    return dados_validos.get(nome_normalizado)


def extrair_nomes_cpfs_intervalo(df, linha_inicial, linha_final, dados_validos):
    """
    Extrai nomes e CPFs de um intervalo de linhas em um DataFrame.

    :param df: DataFrame com as linhas do PDF (colunas "Line Number" e "Text").
    :param linha_inicial: Número da linha inicial no DataFrame.
    :param linha_final: Número da linha final no DataFrame.
    :param dados_validos: Dicionário contendo nomes normalizados e CPFs.
    :return: Dicionário com os nomes encontrados, seus CPFs e linhas.
    """
    # Regex para encontrar nomes
    regex_nome = r"\b[A-ZÁÉÍÓÚÃÕÂÊÔÇ]+(?: [A-ZÁÉÍÓÚÃÕÂÊÔÇ]+)*\b"

    resultados = {}

    # Filtrar o DataFrame para o intervalo de linhas especificado
    df_intervalo = df[(df["Line Number"] >= linha_inicial) & (df["Line Number"] <= linha_final)]

    for _, row in df_intervalo.iterrows():
        linha = row["Text"]
        linha_global = row["Line Number"]

        # Encontrar todos os nomes na linha
        nomes = re.findall(regex_nome, linha)

        for nome in nomes:
            nome_normalizado = unidecode(nome).upper()  # Remove acentos e coloca em maiúsculas

            # Verificar se o nome está no dicionário de dados válidos
            cpf = buscar_cpf_por_nome(nome_normalizado, dados_validos)
            if cpf:
                resultados[nome] = (cpf, linha_global)  # Adicionar o nome, CPF e a linha

    return resultados


def carregar_dados_validos(caminho_csv):
    """
    Carrega os dados de nomes e CPFs do CSV e normaliza os nomes.
    :param caminho_csv: Caminho para o arquivo CSV.
    :return: Dicionário com nomes normalizados e seus respectivos CPFs.
    """
    try:
        # Carrega os dados do CSV
        dados = pd.read_csv(caminho_csv)

        # Certifique-se de que as colunas necessárias existem
        if 'nome' in dados.columns and 'cpf' in dados.columns:
            # Converte colunas para strings e trata valores nulos
            dados['nome'] = dados['nome'].astype(str).fillna("")
            dados['cpf'] = dados['cpf'].astype(str).fillna("CPF AUSENTE")

            # Normaliza os nomes para facilitar a busca (removendo acentos e convertendo para maiúsculas)
            dados['nome_normalizado'] = dados['nome'].apply(lambda x: unidecode(x).upper())

            # Retorna um dicionário com os nomes normalizados e CPFs
            return dict(zip(dados['nome_normalizado'], dados['cpf']))
        else:
            raise ValueError("O arquivo CSV não contém as colunas 'nome' e 'cpf'.")
    except Exception as e:
        print(f"Erro ao carregar dados válidos: {e}")
        return {}