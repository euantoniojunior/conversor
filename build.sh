#!/bin/bash

# Atualizar o sistema e instalar o LibreOffice
apt-get update && \
apt-get install -y libreoffice && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Instalar as dependências Python
pip install --no-cache-dir -r requirements.txt
