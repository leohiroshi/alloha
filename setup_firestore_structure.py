import json

def create_firestore_rules():
    """Criar regras de segurança do Firestore"""
    
    rules = """rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Coleção de mensagens - apenas leitura/escrita por aplicação autenticada
    match /messages/{messageId} {
      allow read, write: if true; // Temporário para desenvolvimento
    }
    
    // Coleção de usuários
    match /users/{userId} {
      allow read, write: if true; // Temporário para desenvolvimento
    }
    
    // Coleção de conversas
    match /conversations/{conversationId} {
      allow read, write: if true; // Temporário para desenvolvimento
    }
    
    // Coleção de analytics
    match /analytics/{analyticsId} {
      allow read, write: if true; // Temporário para desenvolvimento
    }
    
    // Coleção de propriedades/imóveis
    match /properties/{propertyId} {
      allow read: if true; // Público para leitura
      allow write: if true; // Temporário para desenvolvimento
    }
  }
}"""

    with open('firestore.rules', 'w') as f:
        f.write(rules)
    
    print("✅ Arquivo 'firestore.rules' criado!")
    print("📋 Para aplicar no Firebase:")
    print("1. Vá para Firestore Database > Regras")
    print("2. Cole o conteúdo do arquivo firestore.rules")
    print("3. Clique em 'Publicar'")

def create_sample_data():
    """Criar dados de exemplo para testar"""
    
    # Dados de exemplo para propriedades
    sample_properties = [
        {
            "id": "apt_001",
            "type": "apartamento",
            "bedrooms": 2,
            "bathrooms": 1,
            "area": 65,
            "price": 350000,
            "location": "zona_sul",
            "neighborhood": "Copacabana",
            "description": "Apartamento moderno com vista para o mar",
            "amenities": ["piscina", "academia", "portaria_24h"],
            "available": True,
            "created_at": "2025-09-08T00:00:00Z"
        },
        {
            "id": "casa_001", 
            "type": "casa",
            "bedrooms": 3,
            "bathrooms": 2,
            "area": 120,
            "price": 650000,
            "location": "zona_oeste",
            "neighborhood": "Barra da Tijuca",
            "description": "Casa em condomínio fechado com jardim",
            "amenities": ["jardim", "churrasqueira", "garagem_2_vagas"],
            "available": True,
            "created_at": "2025-09-08T00:00:00Z"
        },
        {
            "id": "apt_002",
            "type": "apartamento", 
            "bedrooms": 1,
            "bathrooms": 1,
            "area": 45,
            "price": 280000,
            "location": "centro",
            "neighborhood": "Centro",
            "description": "Studio compacto ideal para jovens profissionais",
            "amenities": ["metro_nearby", "comercio_local"],
            "available": True,
            "created_at": "2025-09-08T00:00:00Z"
        }
    ]
    
    with open('sample_properties.json', 'w', encoding='utf-8') as f:
        json.dump(sample_properties, f, indent=2, ensure_ascii=False)
    
    print("✅ Arquivo 'sample_properties.json' criado!")
    print("📊 Contém 3 propriedades de exemplo para testar")

def show_collection_structure():
    """Mostrar estrutura das coleções"""
    
    structure = """
📁 ESTRUTURA DAS COLEÇÕES FIRESTORE:

🔹 messages/
   ├── user_phone (string)
   ├── message (string)  
   ├── direction (string: "received" | "sent")
   ├── timestamp (timestamp)
   └── metadata (object)

🔹 users/
   ├── phone (string)
   ├── name (string)
   ├── email (string)
   ├── preferences (object)
   ├── created_at (timestamp)
   └── last_updated (timestamp)

🔹 conversations/
   ├── user_phone (string)
   ├── last_message (string)
   ├── last_message_direction (string)
   ├── last_updated (timestamp)
   └── total_messages (number)

🔹 analytics/
   ├── event_type (string)
   ├── timestamp (timestamp)
   ├── data (object)
   └── user_phone (string)

🔹 properties/
   ├── id (string)
   ├── type (string: "apartamento" | "casa" | "kitnet")
   ├── bedrooms (number)
   ├── bathrooms (number)
   ├── area (number)
   ├── price (number)
   ├── location (string)
   ├── neighborhood (string)
   ├── description (string)
   ├── amenities (array)
   ├── available (boolean)
   └── created_at (timestamp)
"""
    
    print(structure)

if __name__ == "__main__":
    print("🏗️  CONFIGURADOR DE ESTRUTURA FIRESTORE")
    print("=" * 50)
    
    create_firestore_rules()
    print()
    create_sample_data() 
    print()
    show_collection_structure()
