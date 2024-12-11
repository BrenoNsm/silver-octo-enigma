import os
import csv

def verificar_e_inicializar_controle(caminho_controle):
    try:
        with open(caminho_controle, mode='r', newline='', encoding='utf-8') as file:
            leitor = csv.reader(file)
            # Verifica se o arquivo não está vazio
            if not any(leitor):
                print(f"O arquivo {caminho_controle} está vazio. Inicializando controle.")
                return []
            else:
                # Se o arquivo tiver dados, lê as linhas
                file.seek(0)  # Volta para o início do arquivo
                return [linha[0] for linha in leitor if linha]  # Adiciona verificação de linha vazia
    except FileNotFoundError:
        print(f"O arquivo {caminho_controle} não encontrado. Inicializando controle.")
        return []
    except Exception as e:
        print(f"Erro ao verificar o arquivo de controle: {e}")
        return []


def registrar_arquivo_processado(nome_arquivo, caminho_controle='arquivos_processados.csv'):
    """
    Registra um arquivo como processado no CSV de controle.
    
    :param nome_arquivo: Nome do arquivo processado
    :param caminho_controle: Caminho para o arquivo CSV de controle
    """
    from datetime import datetime
    
    with open(caminho_controle, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([nome_arquivo, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

def arquivo_ja_processado(nome_arquivo, caminho_controle='arquivos_processados.csv'):
    """
    Verifica se um arquivo já foi processado anteriormente.
    
    :param nome_arquivo: Nome do arquivo a verificar
    :param caminho_controle: Caminho para o arquivo CSV de controle
    :return: True se o arquivo já foi processado, False caso contrário
    """
    arquivos_processados = verificar_e_inicializar_controle(caminho_controle)
    return nome_arquivo in arquivos_processados