import requests
import json

def test_webhook_verification():
    """Testar se o webhook responde à verificação"""
    print("🔍 TESTE 1: Verificação do Webhook")
    print("-" * 50)
    
    verify_url = "https://alloha.app/webhook?hub.mode=subscribe&hub.verify_token=alloha_secret&hub.challenge=TEST123"
    
    try:
        response = requests.get(verify_url, timeout=10)
        if response.status_code == 200 and response.text == "TEST123":
            print("✅ Webhook de verificação funcionando!")
            return True
        else:
            print(f"❌ Webhook falhou: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False

def test_message_processing():
    """Testar processamento de mensagens"""
    print("\n🔍 TESTE 2: Processamento de Mensagens")
    print("-" * 50)
    
    # Simular payload real do WhatsApp
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "711526708720131",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "554137900557",
                        "phone_number_id": "711526708720131"
                    },
                    "messages": [{
                        "from": "5511999999999",
                        "id": "wamid.test_message_001",
                        "timestamp": "1672531200",
                        "text": {
                            "body": "Oi, teste do bot!"
                        },
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    try:
        response = requests.post(
            "https://alloha.app/webhook",
            json=webhook_payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WhatsApp/2.23.20.68"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Mensagem processada com sucesso!")
            print(f"📝 Response: {response.json()}")
            return True
        else:
            print(f"❌ Erro no processamento: {response.status_code}")
            print(f"📝 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False

def check_whatsapp_api_connection():
    """Verificar se conseguimos acessar a API do WhatsApp"""
    print("\n🔍 TESTE 3: Conexão com WhatsApp API")
    print("-" * 50)
    
    # Token do seu .env (NOVO TOKEN ATUALIZADO)
    access_token = "EAFdIh8H8IZCYBPQOOGVt4UUORiq4cMOtVmeHyd8oWG3qzl6xywSCXEjiPR4wJpdVXDzsEJN4GLnsp27zRdsjl5tTd20nruQMtxnA0ZBxHj1eJVYj8q8NADWQErVFivJfEDcpUYP1YwjZASJ8eLf1H8zH5O5fjnXWOZBTYj4492GDGSDGcQ7WLswIi85lzsHjy4e1AHmCw3iA7z1JjNLQ7mZB1PG2f2GtXZCFavb6UYPX7a3Rpy7Dr5ExemgKr9BgZDZD"
    phone_number_id = "711526708720131"
    
    # Testar se o token é válido
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Token do WhatsApp válido!")
            print(f"📱 Número: {data.get('display_phone_number', 'N/A')}")
            print(f"🆔 ID: {data.get('id', 'N/A')}")
            return True
        else:
            print(f"❌ Token inválido ou expirado: {response.status_code}")
            print(f"📝 Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro na verificação do token: {str(e)}")
        return False

def check_app_health():
    """Verificar saúde geral da aplicação"""
    print("\n🔍 TESTE 4: Saúde da Aplicação")
    print("-" * 50)
    
    try:
        response = requests.get("https://alloha.app/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Aplicação online!")
            print(f"🤖 IA: {data.get('ai_service_available', 'N/A')}")
            print(f"📱 WhatsApp: {data.get('access_token_configured', 'N/A')}")
            print(f"🆔 Phone ID: {data.get('phone_number_configured', 'N/A')}")
            print(f"🔐 Verify Token: {data.get('verify_token_configured', 'N/A')}")
            return True
        else:
            print(f"❌ Aplicação com problemas: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False

def show_webhook_config_instructions():
    """Mostrar instruções de configuração do webhook"""
    print("\n📋 CONFIGURAÇÃO DO WEBHOOK NO META DEVELOPERS:")
    print("=" * 60)
    print("1. 🌐 Acesse: https://developers.facebook.com/apps")
    print("2. 📱 Selecione sua app do WhatsApp")
    print("3. ⚙️  Vá para: WhatsApp > Configuration")
    print("4. 🔧 Configure:")
    print("   📍 Webhook URL: https://alloha.app/webhook")
    print("   🔑 Verify token: alloha_secret")
    print("5. ✅ Clique: 'Verify and save'")
    print("6. 📋 Marque os campos:")
    print("   ☑️  messages")
    print("   ☑️  message_deliveries")
    print("   ☑️  message_reads")

if __name__ == "__main__":
    print("🔥 DIAGNÓSTICO COMPLETO DO WHATSAPP BOT")
    print("=" * 60)
    
    # Executar todos os testes
    test1 = check_app_health()
    test2 = test_webhook_verification()
    test3 = check_whatsapp_api_connection()
    test4 = test_message_processing()
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    print(f"🏥 Saúde da App: {'✅' if test1 else '❌'}")
    print(f"🔍 Webhook Verify: {'✅' if test2 else '❌'}")
    print(f"📱 WhatsApp API: {'✅' if test3 else '❌'}")
    print(f"💬 Processamento: {'✅' if test4 else '❌'}")
    
    if all([test1, test2, test3, test4]):
        print("\n🎉 TUDO FUNCIONANDO! O problema pode ser:")
        print("   1. 🔧 Configuração do webhook no Meta Developers")
        print("   2. 📱 Número de teste não autorizado")
        print("   3. ⏱️  Delay na entrega de mensagens")
    else:
        print("\n⚠️  PROBLEMAS DETECTADOS!")
        show_webhook_config_instructions()
    
    print("\n📞 NÚMERO PARA TESTE: +554137900557")
    print("🆔 PHONE NUMBER ID: 711526708720131")
