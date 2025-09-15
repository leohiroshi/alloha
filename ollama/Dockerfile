# Dockerfile para servidor Ollama
FROM ollama/ollama:latest

# Instala curl para health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Define argumentos de build
ARG OLLAMA_MODELS="llama3.1,llama3.2-vision"

# Cria diretório para modelos
RUN mkdir -p /root/.ollama

# Expõe a porta padrão do Ollama
EXPOSE 11434

# Copia o script de inicialização
COPY start-ollama.sh /start-ollama.sh

# Torna o script executável
RUN chmod +x /start-ollama.sh

# Define variáveis de ambiente
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=${OLLAMA_MODELS}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:11434/api/tags || exit 1

# CORREÇÃO: Sobrescrever o ENTRYPOINT e usar CMD
ENTRYPOINT []
CMD ["/start-ollama.sh"]