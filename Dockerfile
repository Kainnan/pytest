FROM python:3.12-slim

ENV GECKODRIVER_VERSION=v0.33.0
ENV DEBIAN_FRONTEND=noninteractive

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
    procps \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Baixar e instalar geckodriver
RUN wget -q "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && tar -xzf "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && mkdir -p /opt/geckodriver \
    && mv geckodriver /opt/geckodriver/ \
    && chmod 755 /opt/geckodriver/geckodriver \
    && ln -s /opt/geckodriver/geckodriver /usr/local/bin/geckodriver \
    && rm "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz"

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretório para cache
RUN mkdir -p /root/.cache/selenium \
    && chmod -R 777 /root/.cache/selenium

# Copiar o código da aplicação
COPY . .

# Comando para executar a aplicação
CMD ["python", "main.py"]