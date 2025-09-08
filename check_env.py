import requests
import json
import os
from dotenv import load_dotenv

def load_local_env():
    """Carregar variáveis do arquivo .env local"""
    env_file = ".env"
    if not os.path.exists(env_file):
        print("❌ Arquivo .env não encontrado!")
        print("📝 Crie um arquivo .env baseado no .env.example")
        return None
    
    load_dotenv(env_file)
    
    local_vars = {
        "WHATSAPP_ACCESS_TOKEN": os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN": os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", ""),
        "WHATSAPP_PHONE_NUMBER_ID": os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        "ABACUS_API_KEY": os.getenv("ABACUS_API_KEY", ""),
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
        "SECRET_KEY": os.getenv("SECRET_KEY", ""),
        "AI_PROVIDER": os.getenv("AI_PROVIDER", ""),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", ""),
        "HOST": os.getenv("HOST", ""),
        "PORT": os.getenv("PORT", "")
    }
    
    return local_vars

def get_azure_env_status():
    """Verificar status das variáveis no Azure via health endpoint"""
    try:
        response = requests.get("https://alloha.app/health", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Erro ao verificar Azure: {str(e)}")
        return None

def compare_environments():
    """Comparar ambiente local vs Azure"""
    print("🔍 COMPARANDO VARIÁVEIS DE AMBIENTE")
    print("=" * 60)
    
    # Carregar variáveis locais
    print("\n📁 Carregando arquivo .env local...")
    local_vars = load_local_env()
    
    if not local_vars:
        return
    
    # Verificar status do Azure
    print("☁️  Verificando Azure Container Apps...")
    azure_status = get_azure_env_status()
    
    if not azure_status:
        print("❌ Não foi possível verificar Azure")
        return
    
    print("\n📊 COMPARAÇÃO:")
    print("-" * 60)
    
    # Comparar configurações importantes
    comparisons = [
        {
            "name": "WhatsApp Access Token",
            "local_key": "WHATSAPP_ACCESS_TOKEN", 
            "azure_key": "access_token_configured",
            "sensitive": True
        },
        {
            "name": "WhatsApp Verify Token",
            "local_key": "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
            "azure_key": "verify_token_configured", 
            "sensitive": False
        },
        {
            "name": "WhatsApp Phone Number ID",
            "local_key": "WHATSAPP_PHONE_NUMBER_ID",
            "azure_key": "phone_number_configured",
            "sensitive": True
        },
        {
            "name": "AI Service",
            "local_key": "ABACUS_API_KEY",
            "azure_key": "ai_service_available",
            "sensitive": True
        }
    ]
    
    for comp in comparisons:
        local_value = local_vars.get(comp["local_key"], "")
        azure_configured = azure_status.get(comp["azure_key"], False)
        
        print(f"\n🔧 {comp['name']}:")
        
        if comp["sensitive"]:
            local_status = "✅ Configurado" if local_value else "❌ Vazio"
            print(f"   📁 Local (.env): {local_status}")
        else:
            print(f"   📁 Local (.env): {local_value}")
        
        azure_status_text = "✅ Configurado" if azure_configured else "❌ Não configurado"
        print(f"   ☁️  Azure: {azure_status_text}")
        
        if (bool(local_value) == azure_configured):
            print(f"   🎯 Status: ✅ SINCRONIZADO")
        else:
            print(f"   🎯 Status: ⚠️  DIVERGENTE")

def show_github_secrets_needed():
    """Mostrar quais secrets são necessários no GitHub"""
    print("\n" + "=" * 60)
    print("🔐 SECRETS NECESSÁRIOS NO GITHUB:")
    print("=" * 60)
    
    secrets = [
        "DOCKER_HUB_TOKEN",
        "AZURE_CREDENTIALS", 
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID", 
        "ABACUS_API_KEY",
        "DATABASE_URL",
        "SECRET_KEY"
    ]
    
    for i, secret in enumerate(secrets, 1):
        print(f"{i:2d}. {secret}")
    
    print(f"\n🔗 Configure em: https://github.com/leohiroshi/alloha/settings/secrets/actions")

def check_specific_values():
    """Verificar valores específicos conhecidos"""
    print("\n" + "=" * 60)
    print("🎯 VERIFICAÇÃO DE VALORES ESPECÍFICOS:")
    print("=" * 60)
    
    # Valores que sabemos
    known_values = {
        "WHATSAPP_PHONE_NUMBER_ID": "711526708720131",
        "WHATSAPP_WEBHOOK_VERIFY_TOKEN": "alloha_secret"
    }
    
    local_vars = load_local_env()
    if not local_vars:
        return
    
    for key, expected in known_values.items():
        local_value = local_vars.get(key, "")
        if local_value == expected:
            print(f"✅ {key}: Correto ({expected})")
        elif local_value:
            print(f"⚠️  {key}: Divergente")
            print(f"   📁 Local: {local_value}")
            print(f"   🎯 Esperado: {expected}")
        else:
            print(f"❌ {key}: Não configurado")

if __name__ == "__main__":
    compare_environments()
    check_specific_values()
    show_github_secrets_needed()
    
    print("\n" + "🎯" * 20)
    print("📋 COMO CORRIGIR DIVERGÊNCIAS:")
    print("1. 📝 Edite o arquivo .env com os valores corretos")
    print("2. 🔐 Atualize os GitHub Secrets se necessário") 
    print("3. 🚀 Faça novo deploy: git commit + git push")
    print("4. ✅ Execute este script novamente para verificar")
