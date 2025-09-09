# Firebase Setup Instructions
# Guia para configurar Firebase para o bot Alloha

## 1. Criar Projeto Firebase
1. Acesse: https://console.firebase.google.com/
2. Clique: "Criar projeto"
3. Nome: "alloha-whatsapp-bot"
4. Ative: Google Analytics (opcional)

## 2. Configurar Firestore
1. No console Firebase: Firestore Database
2. Clique: "Criar banco de dados"
3. Modo: "Produção" (com regras de segurança)
4. Localização: us-central1 (ou mais próximo)

## 3. Obter Credenciais
1. Configurações do projeto (ícone engrenagem)
2. Aba: "Contas de serviço"
3. Clique: "Gerar nova chave privada"
4. Baixar arquivo JSON

## 4. Configurar Regras do Firestore
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Permitir leitura/escrita para aplicação autenticada
    match /{document=**} {
      allow read, write: if true; // Para desenvolvimento
      // Em produção, implementar regras mais restritivas
    }
  }
}
```

## 5. Estrutura das Coleções
- `conversations/` - Conversas por usuário
- `messages/` - Mensagens individuais
- `users/` - Perfis dos usuários
- `analytics/` - Dados de análise
- `properties/` - Catálogo de imóveis
