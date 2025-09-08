import requests

def check_azure_environment():
    """Verificar variáveis no Azure Container Apps"""
    print("☁️  VERIFICANDO VARIÁVEIS NO AZURE")
    print("=" * 50)
    
    try:
        response = requests.get("https://alloha.app/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            print("📊 STATUS DAS CONFIGURAÇÕES:")
            print(f"✅ Sistema: {data.get('status', 'N/A')}")
            print(f"🤖 IA disponível: {data.get('ai_service_available', 'N/A')}")
            print(f"📱 WhatsApp Access Token: {data.get('access_token_configured', 'N/A')}")
            print(f"🆔 Phone Number ID: {data.get('phone_number_configured', 'N/A')}")
            print(f"🔐 Verify Token: {data.get('verify_token_configured', 'N/A')}")
            
            # Verificar se tudo está configurado
            all_configured = all([
                data.get('ai_service_available'),
                data.get('access_token_configured'),
                data.get('phone_number_configured'),
                data.get('verify_token_configured')
            ])
            
            if all_configured:
                print("\n🎉 TODAS AS VARIÁVEIS ESTÃO CONFIGURADAS NO AZURE!")
            else:
                print("\n⚠️  ALGUMAS VARIÁVEIS PODEM ESTAR FALTANDO:")
                if not data.get('ai_service_available'):
                    print("   ❌ ABACUS_API_KEY não configurado")
                if not data.get('access_token_configured'):
                    print("   ❌ WHATSAPP_ACCESS_TOKEN não configurado")
                if not data.get('phone_number_configured'):
                    print("   ❌ WHATSAPP_PHONE_NUMBER_ID não configurado")
                if not data.get('verify_token_configured'):
                    print("   ❌ WHATSAPP_WEBHOOK_VERIFY_TOKEN não configurado")
            
            return data
            
        else:
            print(f"❌ Erro: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return None

def check_github_secrets():
    """Verificar quais secrets estão no GitHub"""
    print("\n🔐 GITHUB SECRETS NECESSÁRIOS:")
    print("=" * 50)
    
    secrets_list = [
        "✅ DOCKER_HUB_TOKEN (já configurado)",
        "✅ AZURE_CREDENTIALS (já configurado)", 
        "? WHATSAPP_WEBHOOK_VERIFY_TOKEN",
        "? WHATSAPP_ACCESS_TOKEN",
        "? WHATSAPP_PHONE_NUMBER_ID",
        "? ABACUS_API_KEY",
        "? DATABASE_URL",
        "? SECRET_KEY"
    ]
    
    for secret in secrets_list:
        print(f"   {secret}")
    
    print(f"\n🔗 Verificar/Configurar em:")
    print("   https://github.com/leohiroshi/alloha/settings/secrets/actions")

if __name__ == "__main__":
    azure_data = check_azure_environment()
    check_github_secrets()
    
    print("\n" + "🎯" * 20)
    print("📋 PRÓXIMOS PASSOS:")
    print("1. 📝 Complete o arquivo .env com valores reais")
    print("2. 🔐 Verifique GitHub Secrets se algo estiver faltando")
    print("3. 🚀 Se mudou algo: git add . && git commit && git push")
    print("4. ✅ Teste enviando mensagem WhatsApp para +554137900557")
