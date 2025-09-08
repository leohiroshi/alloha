import requests
import json

def test_your_whatsapp_setup():
    """Testar configuração específica do seu WhatsApp"""
    base_url = "https://alloha.app"
    
    print("📱 TESTANDO SEU WHATSAPP BUSINESS API")
    print("=" * 60)
    print(f"📞 Número: +554137900557")
    print(f"🆔 Phone ID: 711526708720131")
    print(f"🔗 Webhook: https://alloha.app/webhook")
    print(f"🔑 Verify Token: alloha_secret")
    print("=" * 60)
    
    # Simular webhook do seu número específico
    webhook_payload = {
        "entry": [{
            "id": "711526708720131",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "+554137900557",
                        "phone_number_id": "711526708720131"
                    },
                    "messages": [{
                        "from": "5511999999999",  # Número do cliente teste
                        "id": "wamid.test123",
                        "timestamp": "1672531200",
                        "text": {
                            "body": "Olá! Quero conhecer apartamentos na zona sul de SP"
                        },
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    try:
        print("\n🔄 Enviando mensagem de teste...")
        response = requests.post(
            f"{base_url}/webhook",
            json=webhook_payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WhatsApp/2.0"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ SUCESSO! Webhook processou a mensagem")
            print(f"📝 Response: {response.json()}")
            print("\n🤖 A IA deve ter:")
            print("1. ✅ Analisado a intenção (busca de imóvel)")
            print("2. ✅ Detectado entidades (apartamentos, zona sul)")
            print("3. ✅ Gerado resposta contextual")
            print("4. ✅ Tentado enviar resposta via WhatsApp API")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_health_with_your_config():
    """Verificar se sua configuração está ativa"""
    base_url = "https://alloha.app"
    
    print("\n🏥 VERIFICANDO SAÚDE DO SISTEMA")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Sistema online!")
            print(f"🤖 IA disponível: {data.get('ai_service_available', 'N/A')}")
            print(f"📱 WhatsApp configurado: {data.get('access_token_configured', 'N/A')}")
            print(f"🆔 Phone ID configurado: {data.get('phone_number_configured', 'N/A')}")
            print(f"🔐 Verify token: {data.get('verify_token_configured', 'N/A')}")
            
            if all([
                data.get('ai_service_available'),
                data.get('access_token_configured'),
                data.get('phone_number_configured'),
                data.get('verify_token_configured')
            ]):
                print("\n🎉 TUDO CONFIGURADO CORRETAMENTE!")
            else:
                print("\n⚠️  Algumas configurações podem estar faltando")
        else:
            print(f"❌ Health check falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_webhook_verification():
    """Testar verificação do webhook"""
    base_url = "https://alloha.app"
    
    print("\n🔍 TESTANDO VERIFICAÇÃO DO WEBHOOK")
    print("=" * 60)
    
    verify_url = f"{base_url}/webhook?hub.mode=subscribe&hub.verify_token=alloha_secret&hub.challenge=CHALLENGE_ACCEPTED"
    
    try:
        response = requests.get(verify_url, timeout=10)
        if response.status_code == 200 and response.text == "CHALLENGE_ACCEPTED":
            print("✅ Verificação do webhook funcionando!")
            print(f"📝 Challenge response: {response.text}")
        else:
            print(f"❌ Verificação falhou: {response.status_code}")
            print(f"📝 Response: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_health_with_your_config()
    test_webhook_verification()
    test_your_whatsapp_setup()
    
    print("\n" + "🎯" * 20)
    print("📋 PRÓXIMOS PASSOS:")
    print("1. 🔧 Configure o webhook no Meta Developers:")
    print("   - URL: https://alloha.app/webhook")
    print("   - Token: alloha_secret")
    print("2. 📱 Teste enviando mensagem para +554137900557")
    print("3. 📊 A IA irá responder automaticamente!")
    print("4. 🔍 Monitore logs se necessário")
    print("\n💡 TIPOS DE TESTE:")
    print("   • 'Oi' → Saudação personalizada")
    print("   • 'Quero apartamento' → Busca inteligente")
    print("   • 'Quanto custa?' → Consulta de preços")
    print("   • 'Agendar visita' → Agendamento")
