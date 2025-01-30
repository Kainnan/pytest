# Use a imagem base mais leve com Python 3.12
FROM python:3.12-slim-bookworm

# Versões compativeis com Debian Bookworm
ENV GECKODRIVER_VERSION=v0.34.0
ENV FIREFOX_VERSION=115.12.0esr
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Configurações de ambiente críticas
ENV MOZ_HEADLESS=1
ENV DISPLAY=:99
ENV XDG_CACHE_HOME=/tmp/.cache
ENV GEOMETRY=1024x768x24
ENV FIREFOX_BIN=/opt/firefox/firefox

# Instalar dependências essenciais
RUN apt-get update -qqy && \
    apt-get install -qqy --no-install-recommends \
    ca-certificates \
    wget \
    bzip2 \
    libxt6 \
    libx11-xcb1 \
    libdbus-glib-1-2 \
    libgtk-3-0 \
    libpci3 \
    xvfb \
    fluxbox \
    procps \
    dumb-init && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Instalar Firefox ESR específico
RUN wget -qO /tmp/firefox.tar.bz2 \
    "https://download-installer.cdn.mozilla.net/pub/firefox/releases/${FIREFOX_VERSION}/linux-x86_64/en-US/firefox-${FIREFOX_VERSION}.tar.bz2" && \
    tar -xjf /tmp/firefox.tar.bz2 -C /opt && \
    ln -s /opt/firefox/firefox /usr/local/bin/firefox && \
    rm /tmp/firefox.tar.bz2

# Instalar Geckodriver
RUN wget -qO /tmp/geckodriver.tar.gz \
    "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/geckodriver && \
    rm /tmp/geckodriver.tar.gz

# Configurar ambiente seguro
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/.cache/selenium && \
    chmod -R 777 /home/appuser/.cache && \
    chmod -R 777 /tmp

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código e ajustar permissões
COPY . .
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

USER appuser

# Configurar Xvfb e fluxbox
RUN echo '#!/bin/sh\n\
Xvfb :99 -ac -screen 0 $GEOMETRY -nolisten tcp &\n\
fluxbox &\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/entrypoint.sh"]
CMD ["python", "main.py"]