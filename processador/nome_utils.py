import re
import pandas as pd
from unidecode import unidecode  # Para remover acentos

# Compila uma única vez o padrão de nomes em maiúsculas
REGEX_NOME = re.compile(r"\b[A-ZÁÉÍÓÚÃÕÂÊÔÇ]+(?: [A-ZÁÉÍÓÚÃÕÂÊÔÇ]+)*\b")


def buscar_cpf_por_nome(nome_normalizado, dados_validos):
    """
    Busca o CPF correspondente ao nome normalizado nos dados válidos.
    :param nome_normalizado: Nome normalizado para busca.
    :param dados_validos: Dicionário de nomes normalizados e seus respectivos CPFs.
    :return: CPF correspondente ou None.
    """
    return dados_validos.get(nome_normalizado)


def extrair_nomes_cpfs_intervalo(df, linha_inicial=None, linha_final=None, dados_validos=None):
    """Extrai nomes e CPFs de um intervalo de linhas em um DataFrame.

    Se ``linha_inicial`` e ``linha_final`` forem ``None``, considera ``df`` já
    filtrado. O parâmetro ``dados_validos`` deve ser um dicionário com os nomes
    normalizados e seus respectivos CPFs.
    """
    if dados_validos is None:
        dados_validos = {}

    resultados = {}

    if linha_inicial is not None and linha_final is not None:
        df_intervalo = df[(df["Line Number"] >= linha_inicial) & (df["Line Number"] <= linha_final)]
    else:
        df_intervalo = df

    for linha_num, texto in df_intervalo.itertuples(index=False, name=None):
        for nome in REGEX_NOME.findall(texto):
            nome_normalizado = unidecode(nome).upper()
            cpf = buscar_cpf_por_nome(nome_normalizado, dados_validos)
            if cpf:
                resultados[nome] = (cpf, linha_num)

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
