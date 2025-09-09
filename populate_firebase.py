#!/usr/bin/env python3
"""
Script para popular o Firebase com dados de exemplo
Execute: python populate_firebase.py
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
import json

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firebase_service import FirebaseService

async def populate_firebase():
    """Popular Firebase com dados de exemplo"""
    print("🔥 Iniciando população do Firebase...")
    
    # Inicializar serviço
    firebase_service = FirebaseService()
    
    if not firebase_service.is_connected():
        print("❌ Firebase não conectado! Verifique as credenciais.")
        return
    
    print("✅ Firebase conectado com sucesso!")
    
    # 1. Criar dados de exemplo para usuários
    users_data = [
        {
            "phone_number": "+5541999888777",
            "name": "Maria Silva",
            "email": "maria@email.com",
            "preferences": {
                "tipo_imovel": "apartamento",
                "faixa_preco": "500000-800000",
                "bairros": ["Centro", "Batel", "Água Verde"]
            }
        },
        {
            "phone_number": "+5541888777666",
            "name": "João Santos",
            "email": "joao@email.com", 
            "preferences": {
                "tipo_imovel": "casa",
                "faixa_preco": "300000-600000",
                "bairros": ["Portão", "Santa Felicidade"]
            }
        }
    ]
    
    # 2. Criar mensagens de exemplo
    messages_data = [
        {
            "user_phone": "+5541999888777",
            "message": "Olá! Gostaria de informações sobre apartamentos.",
            "direction": "received"
        },
        {
            "user_phone": "+5541999888777", 
            "message": "Olá Maria! Temos ótimos apartamentos disponíveis. Qual sua faixa de preço?",
            "direction": "sent"
        },
        {
            "user_phone": "+5541888777666",
            "message": "Oi, vocês têm casas na região de Portão?",
            "direction": "received"
        },
        {
            "user_phone": "+5541888777666",
            "message": "Sim João! Temos várias casas em Portão. Gostaria de agendar uma visita?",
            "direction": "sent"
        }
    ]
    
    # 3. Criar dados de analytics
    analytics_data = [
        {
            "event_type": "message_received",
            "user_phone": "+5541999888777",
            "event_data": {
                "intent": "busca_imovel",
                "tipo": "apartamento"
            }
        },
        {
            "event_type": "property_interest", 
            "user_phone": "+5541888777666",
            "event_data": {
                "property_type": "casa",
                "location": "Portão"
            }
        }
    ]
    
    # 4. Criar propriedades de exemplo
    properties_data = [
        {
            "titulo": "Apartamento 3 Quartos - Batel",
            "tipo": "apartamento",
            "preco": 650000,
            "area": 120,
            "quartos": 3,
            "banheiros": 2,
            "garagem": 2,
            "bairro": "Batel",
            "cidade": "Curitiba",
            "descricao": "Excelente apartamento no coração do Batel, com acabamento de primeira.",
            "caracteristicas": ["Academia", "Piscina", "Salão de festas"],
            "disponivel": True
        },
        {
            "titulo": "Casa 4 Quartos - Portão",
            "tipo": "casa", 
            "preco": 480000,
            "area": 200,
            "quartos": 4,
            "banheiros": 3,
            "garagem": 2,
            "bairro": "Portão",
            "cidade": "Curitiba",
            "descricao": "Casa espaçosa em condomínio fechado, ideal para famílias.",
            "caracteristicas": ["Churrasqueira", "Quintal", "Portaria 24h"],
            "disponivel": True
        }
    ]
    
    try:
        # Popular usuários
        print("\n👥 Populando usuários...")
        for user_data in users_data:
            success = await firebase_service.save_user_profile(
                user_data["phone_number"], 
                user_data
            )
            if success:
                print(f"✅ Usuário {user_data['name']} criado")
            else:
                print(f"❌ Erro ao criar usuário {user_data['name']}")
        
        # Popular mensagens
        print("\n💬 Populando mensagens...")
        for msg_data in messages_data:
            success = await firebase_service.save_message(
                msg_data["user_phone"],
                msg_data["message"], 
                msg_data["direction"]
            )
            if success:
                print(f"✅ Mensagem de {msg_data['user_phone']} criada")
            else:
                print(f"❌ Erro ao criar mensagem de {msg_data['user_phone']}")
        
        # Popular analytics
        print("\n📊 Populando analytics...")
        for analytics in analytics_data:
            success = await firebase_service.save_analytics_event(
                analytics["event_type"],
                analytics["user_phone"],
                analytics["event_data"]
            )
            if success:
                print(f"✅ Evento {analytics['event_type']} criado")
            else:
                print(f"❌ Erro ao criar evento {analytics['event_type']}")
        
        # Popular propriedades
        print("\n🏠 Populando propriedades...")
        for prop_data in properties_data:
            # Adicionar timestamp
            prop_data["created_at"] = datetime.now()
            prop_data["updated_at"] = datetime.now()
            
            # Salvar propriedade
            doc_ref = firebase_service.db.collection("properties").document()
            doc_ref.set(prop_data)
            print(f"✅ Propriedade '{prop_data['titulo']}' criada")
        
        print("\n🎉 FIREBASE POPULADO COM SUCESSO!")
        print("🔍 Verifique no Firebase Console:")
        print("   - https://console.firebase.google.com/project/alloha-database/firestore")
        
    except Exception as e:
        print(f"❌ Erro ao popular Firebase: {str(e)}")

if __name__ == "__main__":
    asyncio.run(populate_firebase())
