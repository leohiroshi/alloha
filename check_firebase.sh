#!/bin/bash
# Script para verificar se Firebase foi ativado

echo "🔍 Verificando se Firebase está funcionando..."

# Verificar logs da aplicação
az containerapp logs show --name alloha-backend --resource-group rg-alloha-prod --tail 20 | grep -i firebase

echo ""
echo "💡 Procure por mensagens como:"
echo "   ✅ Firebase inicializado com sucesso"
echo "   ✅ Firebase conectado"
echo ""
echo "❌ Se ainda aparecer 'Firebase offline', verifique:"
echo "   1. Se o secret FIREBASE_CREDENTIALS foi adicionado no GitHub"
echo "   2. Se o deploy foi concluído com sucesso"
