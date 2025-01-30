FROM python:3.12-slim

ENV GECKODRIVER_VERSION=v0.33.0

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    bzip2 \
    libxtst6 \
    libgtk-3-0 \
    libx11-xcb1 \
    libdbus-glib-1-2 \
    libxt6 \
    libpci3 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Baixar e instalar geckodriver durante a construção do container
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && tar -xzf "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && rm "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/

# Criar diretório para geckodriver
RUN mkdir -p /opt/geckodriver \
    && mv /usr/local/bin/geckodriver /opt/geckodriver/ \
    && chmod 755 /opt/geckodriver/geckodriver \
    && ln -s /opt/geckodriver/geckodriver /usr/local/bin/geckodriver

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório para cache do selenium
RUN mkdir -p /root/.cache/selenium \
    && chmod -R 777 /root/.cache/selenium

# Copiar o código da aplicação
COPY . .

# Comando para executar a aplicação
CMD ["python", "main.py"]