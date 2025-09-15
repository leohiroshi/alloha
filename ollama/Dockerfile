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

# Script para inicializar e baixar modelos
COPY <<EOF /start-ollama.sh
#!/bin/bash
set -e

echo "🦙 Iniciando servidor Ollama..."

# Inicia o servidor Ollama em background
ollama serve &
OLLAMA_PID=$!

# Aguarda o servidor estar pronto
echo "⏳ Aguardando servidor Ollama ficar disponível..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
done

echo "✅ Servidor Ollama está rodando!"

# Baixa os modelos especificados
IFS=',' read -ra MODELS <<< "$OLLAMA_MODELS"
for model in "${MODELS[@]}"; do
    model=$(echo "$model" | xargs) # Remove espaços
    if [ ! -z "$model" ]; then
        echo "📥 Baixando modelo: $model"
        ollama pull "$model" || echo "❌ Erro ao baixar modelo: $model"
    fi
done

echo "🎉 Todos os modelos foram processados!"

# Mantém o processo principal rodando
wait $OLLAMA_PID
EOF

# Torna o script executável
RUN chmod +x /start-ollama.sh

# Define variáveis de ambiente
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=${OLLAMA_MODELS}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:11434/api/tags || exit 1

# Comando para iniciar
CMD ["/start-ollama.sh"]