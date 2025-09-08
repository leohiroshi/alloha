import requests
import json

def test_ai_endpoint():
    """Testar endpoint de IA diretamente"""
    base_url = "https://alloha.app"
    
    print("🤖 TESTANDO ENDPOINT DE IA")
    print("=" * 50)
    
    test_messages = [
        "Olá! Como você está?",
        "Quero um apartamento de 2 quartos",
        "Qual o preço de casas na zona sul?",
        "Gostaria de agendar uma visita",
        "Que documentos preciso para financiamento?"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}️⃣ TESTE: {message}")
        try:
            response = requests.post(
                f"{base_url}/test-ai",
                json={
                    "message": message,
                    "user_phone": f"test_user_{i:03d}"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS")
                print(f"🤖 AI Response: {data['ai_response']}")
            elif response.status_code == 404:
                print("⚠️  Endpoint /test-ai não encontrado - vamos testar via webhook")
                break
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

def test_analytics_endpoint():
    """Testar endpoint de analytics"""
    base_url = "https://alloha.app"
    
    print("\n📊 TESTANDO ANALYTICS")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/analytics/test_user_001", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Analytics disponível:")
            print(json.dumps(data, indent=2))
        elif response.status_code == 404:
            print("⚠️  Endpoint /analytics não encontrado")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_via_webhook_simulation():
    """Testar IA via simulação completa de webhook"""
    base_url = "https://alloha.app"
    
    print("\n🔄 TESTANDO IA VIA WEBHOOK (Simulação WhatsApp)")
    print("=" * 50)
    
    test_scenarios = [
        {
            "name": "Saudação",
            "message": "Oi! Tudo bem?"
        },
        {
            "name": "Busca Apartamento",
            "message": "Quero um apartamento de 3 quartos na zona oeste"
        },
        {
            "name": "Consulta Preço",
            "message": "Quanto custa um imóvel de 100m²?"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📱 Cenário: {scenario['name']}")
        print(f"💬 Mensagem: {scenario['message']}")
        
        webhook_payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "5511999887766",
                            "text": {
                                "body": scenario['message']
                            },
                            "id": f"test_{scenario['name'].lower()}",
                            "timestamp": "1672531200"
                        }]
                    }
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"{base_url}/webhook",
                json=webhook_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Processado com sucesso")
                print(f"📝 Response: {response.json()}")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_ai_endpoint()
    test_analytics_endpoint()
    test_via_webhook_simulation()
    
    print("\n" + "🎯" * 20)
    print("🚀 PRÓXIMOS PASSOS PARA TESTE REAL:")
    print("1. 📱 Configure WhatsApp Business API")
    print("2. 🔗 Configure webhook URL: https://alloha.app/webhook")
    print("3. 🔑 Use verify token: alloha_secret")
    print("4. 💬 Envie mensagens reais pelo WhatsApp")
    print("5. 📊 Monitore logs no Azure Container Apps")
