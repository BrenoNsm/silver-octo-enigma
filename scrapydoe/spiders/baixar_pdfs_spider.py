import scrapy
import os
import datetime


class BaixarPdfsSpider(scrapy.Spider):
    name = "baixar_pdfs_spider"
    allowed_domains = ["imprensaoficial.rr.gov.br"]
    start_year = 2022
    current_year = datetime.datetime.now().year

    def start_requests(self):
        # Gerar URLs para cada ano desde o ano de início até o ano atual
        for year in range(self.start_year, self.current_year + 1):
            url = f"https://www.imprensaoficial.rr.gov.br/app/_visualizar/?ano={year}"
            yield scrapy.Request(url, callback=self.parse_ano, cb_kwargs={'year': year})

    def parse_ano(self, response, year):
        # Criar um diretório para armazenar os PDFs do ano, se não existir
        ano_dir = os.path.join('pdfs', str(year))
        if not os.path.exists(ano_dir):
            os.makedirs(ano_dir)

        # Encontrar todos os links para os meses dentro do ano
        mes_links = response.xpath('//a[contains(@href, "mes")]/@href').getall()
        for mes_link in mes_links:
            yield response.follow(mes_link, self.parse_mes, cb_kwargs={'year': year})

    def parse_mes(self, response, year):
        # Encontrar todos os inputs que contêm os valores dos DOEs
        doe_inputs = response.xpath('//input[@name="doe"]/@value').getall()
        for doe_value in doe_inputs:
            # Construir a URL do PDF usando o valor do input
            pdf_url = f"https://www.imprensaoficial.rr.gov.br/app/_edicoes/{doe_value}"
            yield scrapy.Request(pdf_url, callback=self.save_pdf, cb_kwargs={'doe_value': doe_value, 'year': year})

    def save_pdf(self, response, doe_value, year):
        if response.status == 200:  # Certifique-se de que o PDF existe
            # Pegue o nome do arquivo a partir da URL
            file_name = response.url.split('/')[-1]
            # Crie um diretório para o ano, se não existir
            ano_dir = os.path.join('pdfs', str(year))
            if not os.path.exists(ano_dir):
                os.makedirs(ano_dir)

            file_path = os.path.join(ano_dir, file_name)
            
            #verificar se já existe no dir
            if os.path.exists(file_path):
                self.log(f"Arquivo já existe: {file_path}. Pulando para o próximo!")
            #baixa se ele não existe
            else:
                with open(file_path, 'wb') as f:
                    f.write(response.body)
                self.log(f"PDF salvo: {file_path}")
        else:
                self.log(f"PDF não encontrado: {response.url}")

    def handle_error(self, failure):
        self.log(f"Erro ao fazer requisição: {failure}", level=scrapy.log.ERROR)
