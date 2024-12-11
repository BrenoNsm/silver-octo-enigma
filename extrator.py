import pdfplumber
import re
import os
import matplotlib.pyplot as plt
import networkx as nx
import csv
import pandas as pd
import re
import scipy as sp
import psycopg2
from gera_grafo import gerar_grafo_atos, exportar_para_graphml
from controle_arquivos import verificar_e_inicializar_controle, registrar_arquivo_processado, arquivo_ja_processado

# Versao para extracao de nomes de arquivo csv
from extrator_nomes_csv import carregar_dados_validos, extrair_nomes_cpfs_intervalo
# Caminho do CSV
caminho_csv = "servidores_cpf_randomicos.csv"
# Carregar os dados válidos
dados_validos = carregar_dados_validos(caminho_csv)
if not isinstance(dados_validos, dict):
    raise ValueError("Erro: dados_validos não é um dicionário!")
else:
    print(' um dic')
#print(dados_validos)

# Versao para extracao de nomes por meio de acesso ao banco
#from extrator_nomes import extrair_nomes_cpfs_intervalo

# Lista de meses em português com seus respectivos números
meses_portugues = [
    ("janeiro", "01"), ("fevereiro", "02"), ("março", "03"),
    ("abril", "04"), ("maio", "05"), ("junho", "06"),
    ("julho", "07"), ("agosto", "08"), ("setembro", "09"),
    ("outubro", "10"), ("novembro", "11"), ("dezembro", "12")
]

def salvar_atos_em_csv(atos, output_csv_path):
    """
    Salva os atos extraídos em um arquivo CSV.

    :param atos: Lista de dicionários contendo informações dos atos
    :param output_csv_path: Caminho completo para salvar o arquivo CSV
    """
    try:
        # Obter os cabeçalhos a partir das chaves do primeiro dicionário
        if not atos:
            print("Nenhum ato para salvar.")
            return
        headers = atos[0].keys()

        # Criar e salvar o CSV
        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(atos)

        print(f"Arquivo CSV salvo em: {output_csv_path}")
    except Exception as e:
        print(f"Erro ao salvar os atos em CSV: {e}")


def converter_data(data):
    partes = data.lower().split(" de ")

    if len(partes) != 3:
        print(f"Erro na formatação da data: '{data}'")
        return None

    dia = partes[0].zfill(2)
    mes = partes[1]
    ano = partes[2]

    mes_formatado = next((num for pt, num in meses_portugues if pt == mes), None)

    if not mes_formatado:
        print(f"Erro: Mês '{mes}' não encontrado.")
        return None

    return f"{dia}/{mes_formatado}/{ano}"

def extrair_informacoes_fonte(texto):
    padrao_fonte = re.compile(r"Boa Vista-RR, (.+?) Edição N°: (\d+)", re.DOTALL)
    match = padrao_fonte.search(texto)

    if match:
        data_fonte = match.group(1).strip()
        data_formatada = converter_data(data_fonte)

        numero_fonte = match.group(2)
        return {
            "Tipo da Fonte": "DOE",
            "Número da Fonte": numero_fonte,
            "Data da Fonte": data_formatada[-10:] if data_formatada else None
        }
    return None

def carregar_pdf_em_dataframe(texto):
    """
    Carrega o texto extraído do PDF em um DataFrame do Pandas, com número da linha e texto.
    :param texto: Texto extraído do PDF
    :return: DataFrame com colunas 'Line Number' e 'Text'
    """
    linhas = texto.splitlines()
    data = [{"Line Number": i + 1, "Text": line} for i, line in enumerate(linhas)]
    return pd.DataFrame(data)

def extrair_atos_corrigidos(df, info_fonte, dados_validos):
    """
    Extrai atos com linhas corrigidas diretamente no DataFrame, com validação de índices e controle de exceções.
    :param df: DataFrame com as linhas do PDF.
    :param info_fonte: Informações gerais da fonte do PDF.
    :param dados_validos: Dicionário contendo nomes normalizados e CPFs.
    :return: Lista de atos extraídos.
    """
    padrao_ato = re.compile(
        r"^(PORTARIA|DECRETO|ATO|PROCESSO)\s+N[º°]\.?\s+([\w./-]+),?\s*(?:DE\s+(\d{1,2}\s+DE\s+[A-ZÇ]{3,9}\s+DE\s+\d{4}))?",
        re.DOTALL | re.IGNORECASE | re.MULTILINE
    )

    atos = []
    matches = []

    # Identificar todas as ocorrências dos atos
    for i, row in df.iterrows():
        match = padrao_ato.search(row["Text"])
        if match:
            matches.append((i, match))

    for idx, (i, match) in enumerate(matches):
        try:
            tipo = match.group(1).capitalize()
            identificador_completo = match.group(2).strip()

            # Separar número e órgão do identificador
            if "/" in identificador_completo:
                partes = identificador_completo.split("/", 1)
                identificador = partes[0].strip()  # Número antes da barra
                orgao = "/" + partes[1].strip()   # Parte após a barra
            else:
                identificador = identificador_completo  # Apenas o número
                orgao = ""  # Nenhum órgão encontrado

            data = match.group(3).strip() if match.group(3) else info_fonte["Data da Fonte"]

            # Linha inicial
            linha_inicio = df.loc[i, "Line Number"]

            # Linha final
            if idx + 1 < len(matches):
                proxima_linha_inicio = df.loc[matches[idx + 1][0], "Line Number"]
                linha_final = proxima_linha_inicio - 1
            else:
                linha_final = df["Line Number"].iloc[-1]  # Última linha do PDF

            # Validação de linha final
            if linha_final <= linha_inicio:
                print(f"Erro: Linha final ({linha_final}) menor ou igual à linha inicial ({linha_inicio}). Corrigindo...")
                linha_final = linha_inicio + 1

            # Extração do Texto do Ato
            texto_ato = "\n".join(
                df.loc[(df["Line Number"] > linha_inicio) & (df["Line Number"] <= linha_final), "Text"]
            ).strip()

            # Extração de nomes e CPFs usando o DataFrame e dados válidos
            nomes_cpfs = extrair_nomes_cpfs_intervalo(df, linha_inicial=linha_inicio, linha_final=linha_final, dados_validos=dados_validos)

            # Adiciona o ato
            ato = {
                **info_fonte,
                "Tipo do Ato": tipo,
                "Identificador do Ato": identificador,
                "Órgão": orgao,
                "Data do Ato": data,
                "Linha Início": linha_inicio,
                "Linha Final": linha_final,
                "Texto do Ato": texto_ato,  # Novo campo adicionado
                "Nomes e CPFs": nomes_cpfs
            }
            atos.append(ato)
            print(ato)
        except Exception as e:
            print(f"Erro ao processar o ato na linha {i}: {e}")
            continue

    return atos


# Caminho para o PDF
caminho_pdf = "doe-20241101.pdf"
nome_arquivo_pdf = os.path.basename(caminho_pdf)

#verificação antes do processamento
if arquivo_ja_processado(nome_arquivo_pdf):
    print(f"O arquivo {nome_arquivo_pdf} já foi processado anteriormente.")
else:

    if not os.path.exists(caminho_pdf):
        print(f"Arquivo {caminho_pdf} não encontrado!")
    else:
        print(f"Arquivo {caminho_pdf} encontrado.")

        with pdfplumber.open(caminho_pdf) as pdf:
            primeira_pagina = pdf.pages[0].extract_text()
            info_fonte = extrair_informacoes_fonte(primeira_pagina)

            texto = "".join(pagina.extract_text() for pagina in pdf.pages)
            df = carregar_pdf_em_dataframe(texto)

        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 1000)

        resultado = extrair_atos_corrigidos(df, info_fonte, dados_validos)

        # Caminho para o CSV de saída
        output_csv_path = "/home/breno/Documentos/ProjetoPesquisa/extrair_atos_corrigidos.csv"

        # Extração e salvamento
        if resultado:
            salvar_atos_em_csv(resultado, output_csv_path)
        else:
            print("Nenhum resultado para processar.")

        # Gerando o grafo
        G = gerar_grafo_atos(resultado)

        # Visualização do grafo gerado
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(G, seed=42)

        color_map = [
            'skyblue' if G.nodes[node]['tipo'] == 'órgão'
            else 'lightgreen' if G.nodes[node]['tipo'] == 'ato'
            else 'lightcoral'
            for node in G.nodes
        ]

        nx.draw_networkx(
            G, pos, with_labels=True, node_color=color_map,
            node_size=3000, font_size=10, font_color='black', font_weight='bold'
        )

        plt.title("Grafo dos Atos e Pessoas Relacionadas")
        plt.savefig("grafo_atos.png")
        print("Grafo salvo como 'grafo_atos.png'")

        exportar_para_graphml(G, "Grafo_Gephi.graphml")

        # Adicione esta linha após o processamento completo
        registrar_arquivo_processado(nome_arquivo_pdf)