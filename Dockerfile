# Use a imagem base mais leve com Python 3.12
FROM python:3.12-slim-bookworm

ENV GECKODRIVER_VERSION=v0.34.0
ENV FIREFOX_VERSION=115.12.0esr
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Configurações de ambiente críticas para performance
ENV MOZ_HEADLESS=1
ENV DISPLAY=:99
ENV XDG_CACHE_HOME=/tmp/.cache
ENV NO_PROXY=localhost,127.0.0.1
ENV GEOMETRY=1024x768x24

# Instalar apenas dependências essenciais
RUN apt-get update -qqy && \
    apt-get install -qqy --no-install-recommends \
    ca-certificates \
    firefox-esr=${FIREFOX_VERSION} \
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

# Configurar geckodriver
RUN wget -qO /tmp/geckodriver.tar.gz \
    "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/geckodriver && \
    rm /tmp/geckodriver.tar.gz

# Configurar ambiente seguro para o container
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/.cache/selenium && \
    chmod -R 777 /home/appuser/.cache && \
    chmod -R 777 /tmp

WORKDIR /app

# Otimizar instalação de dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código e ajustar permissões
COPY . .
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

USER appuser

# Configurar Xvfb e fluxbox para virtual display
RUN echo '#!/bin/sh\n\
Xvfb :99 -ac -screen 0 $GEOMETRY -nolisten tcp &\n\
fluxbox &\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/usr/bin/dumb-init", "--", "/entrypoint.sh"]
CMD ["python", "main.py"]