# JARVIS WhatsApp UC - Dockerfile
# Chrome indetectável com XVFB + VNC para visualização
#
# Build: docker build -t jarvis-whatsapp .
# Run:   docker run -it --shm-size=2g jarvis-whatsapp

FROM python:3.11-slim

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    # Ferramentas básicas
    wget \
    curl \
    gnupg \
    unzip \
    # Chrome dependencies
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libdrm2 \
    libxshmfence1 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    # Display virtual
    xvfb \
    x11vnc \
    # Limpeza
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (cache de camadas)
COPY requirements.txt requirements_whatsapp_uc.txt* ./

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
    undetected-chromedriver \
    faiss-cpu \
    sentence-transformers \
    redis

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p /app/data/wa_profile /app/logs

# Variáveis de ambiente
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Script de inicialização
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expor porta VNC para visualização
EXPOSE 5900

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Comando padrão
CMD ["python", "jarvis_whatsapp_uc.py"]
