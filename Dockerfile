# Usar uma imagem Python oficial como base
FROM python:3.11-slim

# Instalar o LibreOffice
RUN apt-get update && \
    apt-get install -y libreoffice && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar os arquivos do projeto para o contêiner
COPY . .

# Instalar as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expor a porta do Flask
EXPOSE 5000

# Comando para executar a aplicação
CMD ["gunicorn", "app:app"]
