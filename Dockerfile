# Usando Python oficial
FROM python:3.10-slim

# Instala FFmpeg e Node.js (necessários para o yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cria um usuário para não rodar como root (segurança do Hugging Face)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"

WORKDIR /home/user/app

# Copia os requisitos e instala
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY --chown=user . .

# O Hugging Face usa a porta 7860 por padrão
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]