import pdfplumber
import re
import os
import csv
import pandas as pd
from extrator_nomes_csv import carregar_dados_validos, extrair_nomes_cpfs_intervalo

# Caminho do CSV
caminho_csv = "servidores_cpf_randomicos.csv"
# Carregar os dados válidos
dados_validos = carregar_dados_validos(caminho_csv)
if not isinstance(dados_validos, dict):
    raise ValueError("Erro: dados_validos não é um dicionário!")
else:
    print('um dic')

# Mapeamento de meses em português para números
meses_portugues = {
    "janeiro": "01", "fevereiro": "02", "março": "03",
    "abril": "04", "maio": "05", "junho": "06",
    "julho": "07", "agosto": "08", "setembro": "09",
    "outubro": "10", "novembro": "11", "dezembro": "12"
}

def normalizar_data(data):
    """
    Normaliza diferentes formatos de data para o padrão DD/MM/YYYY.
    Remove o dia da semana, se presente.
    
    Possíveis formatos de entrada:
    - "sexta-feira, 20/09/2024"
    - "18 DE SETEMBRO DE 2024"
    - "18/09/2024"
    - "18-09-2024"
    
    :param data: String representando uma data
    :return: Data no formato DD/MM/YYYY ou None se inválida
    """
    # Remove acentos e converte para minúsculas
    data = data.lower().replace('é', 'e')
    
    # Remove o dia da semana, se presente
    dias_semana = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    for dia in dias_semana:
        data = data.replace(dia + ', ', '').replace(dia, '')
    
    # Remove espaços extras
    data = data.strip()
    
    # Caso seja o formato "DD DE MES DE YYYY"
    if " de " in data:
        try:
            partes = data.split(" de ")
            dia = partes[0].zfill(2)
            mes_texto = partes[1]
            ano = partes[2]
            
            # Converte o mês por extenso para número
            mes = meses_portugues.get(mes_texto)
            
            if not mes:
                print(f"Erro: Mês '{mes_texto}' não reconhecido.")
                return None
            
            return f"{dia}/{mes}/{ano}"
        
        except Exception as e:
            print(f"Erro ao converter data '{data}': {e}")
            return None
    
    # Caso já esteja em formato DD/MM/YYYY ou DD-MM-YYYY
    separadores = ["/", "-"]
    for sep in separadores:
        if sep in data:
            try:
                dia, mes, ano = data.split(sep)
                return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"
            except Exception:
                continue
    
    print(f"Formato de data não reconhecido: {data}")
    return None
    
    # Caso já esteja em formato DD/MM/YYYY ou DD-MM-YYYY
    separadores = ["/", "-"]
    for sep in separadores:
        if sep in data:
            try:
                dia, mes, ano = data.split(sep)
                return f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"
            except Exception:
                continue
    
    print(f"Formato de data não reconhecido: {data}")
    return None

def extrair_informacoes_fonte(texto):
    padrao_fonte = re.compile(r"Boa Vista-RR, (.+?) Edição N°: (\d+)", re.DOTALL)
    match = padrao_fonte.search(texto)

    if match:
        data_fonte = match.group(1).strip()
        data_formatada = normalizar_data(data_fonte)

        numero_fonte = match.group(2)
        return {
            "Tipo da Fonte": "DOE",
            "Número da Fonte": numero_fonte,
            "Data da Fonte": data_formatada
        }
    return None

def salvar_atos_em_csv(atos, output_csv_path):
    """
    Salva os atos extraídos em um arquivo CSV, expandindo nomes e CPFs.
    """
    try:
        # Lista expandida para armazenar linhas
        linhas_expandidas = []

        for ato in atos:
            # Copia todas as informações do ato exceto Nomes e CPFs
            info_base = {k: v for k, v in ato.items() if k != "Nomes e CPFs"}
            
            # Verifica se há nomes e CPFs para expandir
            if isinstance(ato.get("Nomes e CPFs"), dict):
                # Expandir para cada nome/CPF
                for nome, (cpf, _) in ato["Nomes e CPFs"].items():
                    # Cria uma cópia do dicionário base
                    linha = info_base.copy()
                    
                    # Adiciona nome e CPF
                    linha["Nome"] = nome
                    linha["CPF"] = cpf
                    
                    linhas_expandidas.append(linha)
            else:
                # Se não houver nomes/CPFs, adiciona a linha original
                linhas_expandidas.append(ato)

        # Verifica se há linhas para salvar
        if not linhas_expandidas:
            print("Nenhum ato para salvar.")
            return

        # Obtém os cabeçalhos
        headers = linhas_expandidas[0].keys()

        # Criar e salvar o CSV
        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(linhas_expandidas)

        print(f"Arquivo CSV salvo em: {output_csv_path}")
    except Exception as e:
        print(f"Erro ao salvar os atos em CSV: {e}")

# [Resto do código permanece igual ao script anterior]
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
    # Ajuste no padrão para capturar o identificador do ato corretamente
    padrao_ato = re.compile(
        r"^(PORTARIA|DECRETO|ATO|PROCESSO)\s+N[º°]\.?\s+([\w./-]+(?:/[A-Za-z]+)?(?:\s*[-\w/]+)*),?\s*(?:DE\s+(\d{1,2}\s+DE\s+[A-ZÇ]{3,9}\s+DE\s+\d{4}))?",
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
            identificador = match.group(2).strip()
            
            # Se a data não estiver no ato, usa a data da fonte
            data_ato = match.group(3).strip() if match.group(3) else info_fonte["Data da Fonte"]
            data_ato_formatada = normalizar_data(data_ato)

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

            # Extração de nomes e CPFs usando o DataFrame e dados válidos
            nomes_cpfs = extrair_nomes_cpfs_intervalo(df, linha_inicial=linha_inicio, linha_final=linha_final, dados_validos=dados_validos)

            # Extração do texto do ato
            texto_ato = " ".join(df.loc[linha_inicio-1:linha_final-1, "Text"].tolist())

            # Adiciona o ato
            ato = {
                **info_fonte,
                "Tipo do Ato": tipo,
                "Identificador do Ato": identificador,  # Agora captura o identificador completo
                "Data do Ato": data_ato_formatada,
                "Linha Início": linha_inicio,
                "Linha Final": linha_final,
                "Texto do Ato": texto_ato,  # Nova coluna com o texto do ato
                "Nomes e CPFs": nomes_cpfs
            }
            atos.append(ato)
            print(ato)
        except Exception as e:
            print(f"Erro ao processar o ato na linha {i}: {e}")
            continue

    return atos


# Caminho para o PDF
caminho_pdf = "doe-20240920.pdf"

if not os.path.exists(caminho_pdf):
    print(f"Arquivo {caminho_pdf} não encontrado!")
else:
    print(f"Arquivo {caminho_pdf} encontrado.")

    with pdfplumber.open(caminho_pdf) as pdf:
        primeira_pagina = pdf.pages[0].extract_text()
        info_fonte = extrair_informacoes_fonte(primeira_pagina)

        texto = "".join(pagina.extract_text() for pagina in pdf.pages)
        df = carregar_pdf_em_dataframe(texto)

    pd.set_option("display.max_rows", None)  # Mostra todas as linhas
    pd.set_option("display.max_columns", None)  # Mostra todas as colunas
    pd.set_option("display.width", 1000)  # Ajusta a largura da saída

    resultado = extrair_atos_corrigidos(df, info_fonte, dados_validos)

    # Caminho para o CSV de saída
    output_csv_path = "saida_processamento.csv"

    # Extração e salvamento
    if resultado:  # Supondo que `resultado` contém os atos extraídos
        salvar_atos_em_csv(resultado, output_csv_path)
    else:
        print("Nenhum resultado para processar.")