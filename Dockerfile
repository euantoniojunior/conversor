# Usar uma imagem Python oficial como base
FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice \
        poppler-utils \
        libgl1 \
        libsm6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Criar um usuário não-root para segurança
RUN adduser --disabled-password --gecos '' appuser
USER appuser
WORKDIR /home/appuser/app

# Copiar os arquivos do projeto para o contêiner
COPY --chown=appuser:appuser . .

# Instalar as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expor a porta do Flask
EXPOSE 5000

# Comando para executar a aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
