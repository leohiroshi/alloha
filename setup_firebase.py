import json
import base64

def process_firebase_credentials():
    """Processar credenciais do Firebase para uso no projeto"""
    
    print("🔐 PROCESSADOR DE CREDENCIAIS FIREBASE")
    print("=" * 50)
    
    # Instruções
    print("📋 INSTRUÇÕES:")
    print("1. Baixe o arquivo JSON das credenciais do Firebase")
    print("2. Coloque o arquivo na pasta do projeto")
    print("3. Execute este script")
    print()
    
    # Solicitar arquivo
    filename = input("📁 Nome do arquivo JSON baixado (ex: firebase-adminsdk-xxx.json): ")
    
    try:
        # Ler arquivo JSON
        with open(filename, 'r') as f:
            credentials = json.load(f)
        
        print("✅ Arquivo lido com sucesso!")
        print(f"📊 Project ID: {credentials.get('project_id', 'N/A')}")
        print(f"📧 Client Email: {credentials.get('client_email', 'N/A')}")
        
        # Converter para string compacta
        credentials_str = json.dumps(credentials, separators=(',', ':'))
        
        # Converter para base64 (para GitHub Secrets)
        credentials_b64 = base64.b64encode(credentials_str.encode()).decode()
        
        print("\n" + "=" * 50)
        print("🔑 CREDENCIAIS PROCESSADAS:")
        print("=" * 50)
        
        # Salvar como arquivo .env local
        env_content = f"""
# Firebase Credentials (Local Development)
FIREBASE_CREDENTIALS={credentials_str}

# Firebase Credentials Base64 (Para GitHub Secrets)
# Use este valor no GitHub Secret: FIREBASE_CREDENTIALS
FIREBASE_CREDENTIALS_B64={credentials_b64}

# Firebase Project Info
FIREBASE_PROJECT_ID={credentials.get('project_id', '')}
"""
        
        with open('firebase-config.env', 'w') as f:
            f.write(env_content.strip())
        
        print("✅ Arquivo 'firebase-config.env' criado!")
        print()
        print("📋 PRÓXIMOS PASSOS:")
        print("1. 📝 Copie as credenciais do firebase-config.env para seu .env")
        print("2. 🔐 Adicione FIREBASE_CREDENTIALS_B64 ao GitHub Secrets")
        print("3. 🚀 Faça deploy para testar")
        print()
        print("🔗 GitHub Secrets: https://github.com/leohiroshi/alloha/settings/secrets/actions")
        print("🔑 Nome do Secret: FIREBASE_CREDENTIALS")
        print(f"💾 Valor do Secret: {credentials_b64[:50]}...")
        
        return credentials
        
    except FileNotFoundError:
        print(f"❌ Arquivo '{filename}' não encontrado!")
        print("📝 Certifique-se de baixar o arquivo do Firebase e colocá-lo nesta pasta")
        return None
    except json.JSONDecodeError:
        print("❌ Erro ao ler arquivo JSON!")
        print("📝 Certifique-se de que o arquivo é um JSON válido")
        return None
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return None

if __name__ == "__main__":
    process_firebase_credentials()
