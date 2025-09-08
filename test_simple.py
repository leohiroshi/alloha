import requests
import json

def test_basic_endpoints():
    """Testar endpoints básicos primeiro"""
    base_url = "https://alloha.app"
    
    print("🧪 TESTANDO ENDPOINTS BÁSICOS")
    print("=" * 50)
    
    # Teste 1: Root endpoint
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"✅ Root (/): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Version: {data.get('version', 'N/A')}")
            print(f"   Service: {data.get('service', 'N/A')}")
    except Exception as e:
        print(f"❌ Root: {str(e)}")
    
    # Teste 2: Health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"✅ Health: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   AI Available: {data.get('ai_service_available', 'N/A')}")
            print(f"   WhatsApp: {data.get('access_token_configured', 'N/A')}")
    except Exception as e:
        print(f"❌ Health: {str(e)}")
    
    # Teste 3: Webhook verification
    try:
        webhook_url = f"{base_url}/webhook?hub.mode=subscribe&hub.verify_token=alloha_secret&hub.challenge=test123"
        response = requests.get(webhook_url, timeout=10)
        print(f"✅ Webhook: {response.status_code}")
        if response.status_code == 200:
            print(f"   Challenge Response: {response.text}")
    except Exception as e:
        print(f"❌ Webhook: {str(e)}")

def test_ai_with_webhook_simulation():
    """Simular mensagem do WhatsApp para testar IA"""
    base_url = "https://alloha.app"
    
    print("\n🤖 TESTANDO IA COM SIMULAÇÃO DE WEBHOOK")
    print("=" * 50)
    
    # Simular payload do WhatsApp
    webhook_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "5511999999999",
                        "text": {
                            "body": "Olá! Quero um apartamento de 2 quartos na zona sul"
                        },
                        "id": "test_message_001",
                        "timestamp": "1672531200"
                    }],
                    "metadata": {
                        "phone_number_id": "123456789"
                    }
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
        print(f"✅ Webhook POST: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Webhook POST: {str(e)}")

def test_docs_endpoint():
    """Testar endpoint de documentação"""
    base_url = "https://alloha.app"
    
    print("\n📚 TESTANDO DOCUMENTAÇÃO")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/docs", timeout=10)
        print(f"✅ Docs: {response.status_code}")
        if response.status_code == 200:
            print("   📖 Documentação disponível em: https://alloha.app/docs")
    except Exception as e:
        print(f"❌ Docs: {str(e)}")

if __name__ == "__main__":
    test_basic_endpoints()
    test_ai_with_webhook_simulation()
    test_docs_endpoint()
    
    print("\n" + "=" * 50)
    print("🎯 COMO TESTAR A IA COMPLETA:")
    print("1. 📱 Envie mensagem pelo WhatsApp para seu número")
    print("2. 🌐 Visite https://alloha.app/docs para ver todos endpoints")
    print("3. 🔍 Use https://alloha.app/health para monitorar status")
    print("4. 📊 Logs disponíveis no Azure Container Apps")
