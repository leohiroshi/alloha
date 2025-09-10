"""
COMO LIMPAR CONVERSAS PARA SIMULAR LEAD NOVO
============================================

🎯 OPÇÃO 1: SCRIPT PYTHON (Recomendado)
---------------------------------------
Execute no terminal:
```
python clear_conversations.py
```

🎯 OPÇÃO 2: REINICIAR APLICAÇÃO (Mais Rápido)
---------------------------------------------
1. No Azure, reinicie a Container App
2. O cache de conversas será limpo automaticamente
3. As conversas do Firebase ficam salvas

🎯 OPÇÃO 3: TESTAR COM NÚMERO DIFERENTE
--------------------------------------
1. Use um número de WhatsApp diferente
2. O bot vai tratar como novo lead automaticamente

🎯 OPÇÃO 4: LIMPAR MANUALMENTE NO FIREBASE
-----------------------------------------
1. Acesse o Firebase Console
2. Vá em Firestore Database
3. Exclua a collection 'messages'

🔧 COMANDOS RÁPIDOS NO TERMINAL:
===============================

# Executar o limpador
python clear_conversations.py

# Ou usar o Azure CLI para reiniciar a app
az containerapp restart --name alloha --resource-group <seu-resource-group>

📱 TESTE APÓS LIMPEZA:
=====================
1. Envie uma foto de imóvel
2. Sofia vai responder como se fosse a primeira vez
3. Histórico de conversa zerado

💡 DICAS:
=========
- Use números diferentes para testes
- O cache se limpa sozinho após reinicialização
- Firebase mantém histórico até você limpar manualmente
