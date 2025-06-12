# Exploração de Padrões em Diários Oficiais com Expressões Regulares e Redes Complexas: Um Modelo para Auditoria e Controle
# UNIVERSIDADE ESTADUAL DE RORAIMA 
**CIÊNCIA DA COMPUTAÇÃO**

**Equipe**
| Acadêmicos | Professores Orientadores |
|--------------|--------------|
| Breno Nascimento |Dr. Bruno César Barreto de Figueirêdo
| Matheus Vicente |Mestre Francisco Carlos de Lima Pereira
| Larisa Carvalho |
| Gabriela Monteiro |

**Professores Orientadores**
Dr. Bruno César Barreto de Figueirêdo,
Mestre Francisco Carlos de Lima Pereira
    

## Visão Geral
Este projeto realiza a extração, processamento e visualização de dados de diários oficiais estaduais, com foco na obtenção de informações sobre servidores públicos. O pipeline do projeto é composto por três etapas principais:

1. **Coleta de dados**: Download dos diários oficiais.
2. **Processamento**: Extração de informações relevantes dos documentos.
3. **Visualização**: Backend para apresentação da rede de conexões e relatórios.

## Estrutura do Projeto

O projeto está organizado nos seguintes diretórios e arquivos principais:

```
├── scrapydoe/
│   ├── spiders/
│   │   ├── baixar_pdfs_spider.py
│   ├── ...
├── processador/
│   ├── extrator.py
│   ├── nome_utils.py
│   ├── db.py
│   ├── servidores_cpf_randomicos.csv
├── backend/
│   ├── app.py
├── web/
│   ├── package.json
│   ├── package-lock.json
│   ├── ...
├── README.md
```

### 1. Coleta de Dados: `baixar_pdfs_spider.py`
Este script está localizado no diretório `scrapydoe/spiders/` e utiliza o framework **Scrapy** para baixar arquivos PDF dos diários oficiais estaduais. Ele acessa os portais governamentais, identifica os diários mais recentes e faz o download dos documentos.

### 2. Processamento dos Dados: `extrator.py`
O script `extrator.py` tem a função de extrair informações relevantes dos arquivos PDF baixados, como atos administrativos, nomeações e exonerações. Os dados processados são armazenados em um banco de dados para posterior análise e visualização.

Para facilitar a análise sem necessidade de execução completa do pipeline, já existe um arquivo `servidores_cpf_randomicos.csv`, contendo dados previamente processados.

### 3. Backend e Web para Visualização
O backend disponibiliza serviços para visualização dos dados extraídos. Ele fornece uma interface para explorar as conexões entre servidores públicos e acessar relatórios detalhados.

A interface web depende das bibliotecas JavaScript especificadas nos arquivos `package.json` e `package-lock.json`, garantindo que todas as dependências estejam corretamente instaladas para o funcionamento adequado do serviço.

## Como Utilizar

### Requisitos
- Python 3.8+
- Dependências listadas no `requirements.txt`
- Banco de dados configurado para armazenamento dos dados extraídos
- Node.js e npm para rodar a interface web

### Execução
1. Clone o repositório:
   ```sh
   git clone https://github.com/BrenoNsm/silver-octo-enigma.git
   cd silver-octo-enigma
   ```

2. Instale as dependências do backend:
   ```sh
   pip install -r requirements.txt
   ```

3. Instale as dependências da interface web:
   ```sh
   npm install
   ```

4. Rode o spider para baixar novos PDFs:
   ```sh
   cd scrapydoe
   scrapy crawl baixar_pdfs_spider
   ```

5. Extraia as informações dos PDFs:
   ```sh
   python processador/extrator.py
   ```

6. Inicie o backend:
   ```sh
   python backend/app.py
   ```

### Rota de fiscalização
O backend possui a rota `/fiscalizacao` que realiza uma análise resumida dos
dados para identificar possíveis irregularidades utilizando a IA Gemini. Para
utilizar essa funcionalidade é necessário definir a variável de ambiente
`GEMINI_API_KEY` com a sua chave de API antes de executar o servidor.

