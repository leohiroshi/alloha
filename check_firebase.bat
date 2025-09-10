@echo off
echo 🔍 Verificando logs mais recentes do Firebase...
echo.

az containerapp logs show --name alloha-backend --resource-group rg-alloha-prod --tail 30

echo.
echo 💡 Procure por estas mensagens:
echo    ✅ Firebase inicializado com sucesso
echo    ✅ Firebase conectado  
echo    ❌ Firebase não configurado (se ainda aparecer, há problema)
echo.
echo 📋 Se ainda mostrar "Firebase offline", verifique:
echo    1. Se o secret FIREBASE_CREDENTIALS existe no GitHub
echo    2. Se o deploy terminou sem erros
