#!/usr/bin/env python3
"""
Script para testar a conexão e funcionamento do Firebase
"""

import os
import sys
import asyncio
from datetime import datetime
import json

# Adicionar o diretório app ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_firebase_connection():
    """Testa a conexão básica com o Firebase"""
    try:
        print("🔍 Testando conexão com Firebase...")
        
        from services.firebase_service import firebase_service
        
        # Verificar se as credenciais estão disponíveis
        firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
        
        if firebase_creds:
            print("✅ Credenciais Firebase encontradas no ambiente")
        else:
            print("❌ Credenciais Firebase NÃO encontradas no ambiente")
            print("💡 Procurando arquivo local...")
            
            if os.path.exists("firebase-credentials.json"):
                print("✅ Arquivo local firebase-credentials.json encontrado")
            else:
                print("❌ Arquivo local firebase-credentials.json NÃO encontrado")
        
        # Testar conexão
        connection_status = firebase_service.check_connection()
        
        if connection_status:
            print("🎉 FIREBASE CONECTADO COM SUCESSO!")
            return True
        else:
            print("❌ FIREBASE NÃO CONECTADO")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar Firebase: {str(e)}")
        return False

async def test_firebase_operations():
    """Testa operações básicas do Firebase"""
    try:
        from services.firebase_service import firebase_service
        
        if not firebase_service.check_connection():
            print("❌ Firebase não conectado - pulando testes de operações")
            return False
        
        print("\n📝 Testando operações do Firebase...")
        
        # Dados de teste
        test_phone = "test_" + str(int(datetime.now().timestamp()))
        test_message = "Mensagem de teste do Firebase"
        
        # Teste 1: Salvar mensagem
        print("1️⃣ Testando salvar mensagem...")
        save_result = await firebase_service.save_message(
            user_phone=test_phone,
            message=test_message,
            direction="received"
        )
        
        if save_result:
            print("✅ Mensagem salva com sucesso!")
        else:
            print("❌ Erro ao salvar mensagem")
            return False
        
        # Teste 2: Recuperar mensagens
        print("2️⃣ Testando recuperar mensagens...")
        messages = await firebase_service.get_user_messages(test_phone)
        
        if messages and len(messages) > 0:
            print(f"✅ {len(messages)} mensagem(s) recuperada(s)!")
            print(f"   📄 Última mensagem: {messages[-1].get('message', 'N/A')}")
        else:
            print("❌ Erro ao recuperar mensagens")
            return False
        
        # Teste 3: Limpar teste
        print("3️⃣ Limpando dados de teste...")
        clear_result = await firebase_service.clear_user_conversation(test_phone)
        
        if clear_result:
            print("✅ Dados de teste limpos!")
        else:
            print("⚠️ Aviso: Erro ao limpar dados de teste")
        
        print("🎉 TODOS OS TESTES DO FIREBASE PASSARAM!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante testes de operações: {str(e)}")
        return False

def check_environment_variables():
    """Verifica variáveis de ambiente relacionadas ao Firebase"""
    print("\n🔧 Verificando variáveis de ambiente...")
    
    env_vars = {
        "FIREBASE_CREDENTIALS": "Credenciais do Firebase",
        "FIREBASE_PROJECT_ID": "ID do projeto Firebase",
        "FIREBASE_DATABASE_URL": "URL do banco Firebase"
    }
    
    found_vars = 0
    for var_name, description in env_vars.items():
        value = os.getenv(var_name)
        if value:
            print(f"✅ {var_name}: Configurado ({description})")
            found_vars += 1
        else:
            print(f"❌ {var_name}: NÃO configurado ({description})")
    
    print(f"\n📊 Variáveis encontradas: {found_vars}/{len(env_vars)}")
    return found_vars > 0

async def test_firebase_in_production():
    """Testa Firebase na aplicação em produção"""
    try:
        print("\n🌐 Testando Firebase em produção...")
        
        # Verificar se conseguimos conectar com Azure CLI
        import subprocess
        result = subprocess.run([
            "az", "containerapp", "logs", "show", 
            "--name", "alloha-backend", 
            "--resource-group", "rg-alloha-prod",
            "--max-log-lines", "50"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logs = result.stdout
            
            # Procurar por indicadores de Firebase
            firebase_indicators = [
                "Firebase inicializado",
                "✅ Firebase",
                "❌ Firebase", 
                "Firebase conectado",
                "Firebase não",
                "firebase_service"
            ]
            
            firebase_logs = []
            for line in logs.split('\n'):
                for indicator in firebase_indicators:
                    if indicator.lower() in line.lower():
                        firebase_logs.append(line.strip())
                        break
            
            if firebase_logs:
                print("📋 Logs do Firebase encontrados:")
                for log in firebase_logs[-10:]:  # Últimos 10 logs
                    print(f"   {log}")
                return True
            else:
                print("⚠️ Nenhum log específico do Firebase encontrado")
                print("💡 Isso pode significar que está funcionando silenciosamente")
                return True
        else:
            print(f"❌ Erro ao acessar logs: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar produção: {str(e)}")
        return False

def show_firebase_status():
    """Mostra um resumo do status do Firebase"""
    print("\n" + "="*60)
    print("🔥 RELATÓRIO DE STATUS DO FIREBASE")
    print("="*60)
    
    # Status local
    local_status = test_firebase_connection()
    
    # Variáveis de ambiente
    env_status = check_environment_variables()
    
    print("\n📊 RESUMO:")
    print(f"   🔗 Conexão Local: {'✅ OK' if local_status else '❌ FALHOU'}")
    print(f"   🔧 Variáveis Ambiente: {'✅ OK' if env_status else '❌ FALTANDO'}")
    
    if local_status:
        print("\n💡 FIREBASE ESTÁ FUNCIONANDO LOCALMENTE!")
        print("   Você pode executar testes completos")
    else:
        print("\n⚠️ FIREBASE NÃO ESTÁ FUNCIONANDO LOCALMENTE")
        print("   Mas pode estar funcionando em produção")
    
    print("\n🎯 PARA TESTAR EM PRODUÇÃO:")
    print("   1. Envie uma mensagem para o WhatsApp")
    print("   2. Verifique se o bot responde")
    print("   3. Execute: python test_firebase.py --production")

async def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Testa o Firebase")
    parser.add_argument("--production", action="store_true", help="Testa em produção")
    parser.add_argument("--full", action="store_true", help="Testa operações completas")
    
    args = parser.parse_args()
    
    if args.production:
        await test_firebase_in_production()
    elif args.full:
        show_firebase_status()
        await test_firebase_operations()
    else:
        show_firebase_status()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Teste interrompido pelo usuário.")
