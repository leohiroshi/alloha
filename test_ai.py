import requests
import json

# URL do seu bot
BASE_URL = "https://alloha.app"

def test_ai_response(message, user_phone="test_user_123"):
    """Testar resposta da IA"""
    try:
        response = requests.post(
            f"{BASE_URL}/test-ai",
            json={
                "message": message,
                "user_phone": user_phone
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ INPUT: {data['input_message']}")
            print(f"🤖 AI RESPONSE: {data['ai_response']}")
            print("-" * 50)
            return data['ai_response']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def test_conversation_flow():
    """Testar fluxo de conversa completo"""
    print("🧪 TESTANDO IA AVANÇADA - ALLOHA BOT")
    print("=" * 60)
    
    user_phone = "test_conversation_001"
    
    # Teste 1: Saudação
    print("1️⃣ TESTE: Saudação")
    test_ai_response("Oi!", user_phone)
    
    # Teste 2: Busca de imóvel
    print("2️⃣ TESTE: Busca de apartamento")
    test_ai_response("Quero um apartamento de 2 quartos na zona sul", user_phone)
    
    # Teste 3: Consulta de preço
    print("3️⃣ TESTE: Consulta de preço")
    test_ai_response("Qual o preço de apartamentos de 2 quartos?", user_phone)
    
    # Teste 4: Agendamento
    print("4️⃣ TESTE: Agendamento de visita")
    test_ai_response("Gostaria de agendar uma visita", user_phone)
    
    # Teste 5: Informações
    print("5️⃣ TESTE: Documentação")
    test_ai_response("Que documentos preciso para comprar?", user_phone)
    
    # Teste 6: Conversa contextual
    print("6️⃣ TESTE: Contexto (baseado na conversa anterior)")
    test_ai_response("E para financiar?", user_phone)

def get_analytics(user_phone="test_conversation_001"):
    """Obter analytics do usuário"""
    try:
        response = requests.get(f"{BASE_URL}/analytics/{user_phone}")
        if response.status_code == 200:
            data = response.json()
            print("📊 ANALYTICS:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Analytics Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Analytics Exception: {str(e)}")

if __name__ == "__main__":
    # Testar fluxo completo
    test_conversation_flow()
    
    print("\n" + "=" * 60)
    print("📊 OBTENDO ANALYTICS...")
    get_analytics()
