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
