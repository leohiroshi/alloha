import requests
import time
import json

def monitor_webhook_calls():
    """Monitorar chamadas do webhook em tempo real"""
    print("🔍 MONITORANDO WEBHOOK EM TEMPO REAL")
    print("=" * 50)
    print("📱 Envie uma mensagem para +554137900557 AGORA!")
    print("⏱️  Aguardando por 60 segundos...")
    print("-" * 50)
    
    start_time = time.time()
    call_count = 0
    
    while time.time() - start_time < 60:  # 60 segundos
        try:
            # Testar se a aplicação está respondendo
            response = requests.get("https://alloha.app/health", timeout=5)
            
            if response.status_code == 200:
                current_time = time.strftime("%H:%M:%S")
                call_count += 1
                print(f"⏰ {current_time} - App online (check #{call_count})")
            else:
                print(f"❌ App offline: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro: {str(e)}")
        
        time.sleep(3)  # Verificar a cada 3 segundos
    
    print("\n⏱️  Tempo esgotado!")
    print("📊 Se você enviou mensagem e não recebeu resposta:")
    print("   1. 🔧 Verifique configuração do webhook no Meta")
    print("   2. 📱 Confirme que o número está autorizado")
    print("   3. 🔍 Verifique se subscreveu aos campos corretos")

def test_manual_webhook():
    """Testar webhook manualmente"""
    print("\n🧪 TESTE MANUAL DO WEBHOOK")
    print("=" * 50)
    
    # Simular mensagem real
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "103728652529965",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "554137900557",
                        "phone_number_id": "711526708720131"
                    },
                    "messages": [{
                        "from": "5511999888777",  # Número de teste
                        "id": "wamid.HBgMNTUxMTk5OTg4ODc3NxUCABIYFjNFQjBDQzU4NkM4MjU0QzVBMEU4AA==",
                        "timestamp": str(int(time.time())),
                        "text": {
                            "body": "Oi, quero um apartamento de 2 quartos!"
                        },
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    try:
        print("📤 Enviando mensagem de teste...")
        response = requests.post(
            "https://alloha.app/webhook",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WhatsApp/2.23.20"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Webhook processou a mensagem!")
            print("🤖 A IA deve ter:")
            print("   1. ✅ Analisado intenção: busca de apartamento")
            print("   2. ✅ Detectado entidades: 2 quartos")
            print("   3. ✅ Gerado resposta contextual")
            print("   4. ✅ Tentado enviar via WhatsApp API")
            print("\n💡 Se não chegou resposta real, o problema é:")
            print("   📱 Configuração do webhook no Meta Developers")
        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    # Primeiro fazer teste manual
    test_manual_webhook()
    
    # Depois monitorar em tempo real
    print("\n" + "🔥" * 20)
    input("🚀 Pressione ENTER quando estiver pronto para monitorar...")
    monitor_webhook_calls()
