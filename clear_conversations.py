#!/usr/bin/env python3
"""
Script para limpar conversas antigas do Firebase
Simula um ambiente limpo para novos leads
"""

import os
import sys
import asyncio
from datetime import datetime

# Adicionar o diretório app ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from services.firebase_service import firebase_service
    from services.ai_service import AIService
except ImportError as e:
    print(f"❌ Erro na importação: {e}")
    print("💡 Certifique-se de estar no diretório correto e ter as dependências instaladas")
    sys.exit(1)

async def clear_all_conversations():
    """Limpa todas as conversas do Firebase e cache"""
    try:
        print("🔥 Iniciando limpeza completa das conversas...")
        
        # Verificar conexão com Firebase
        if not firebase_service.check_connection():
            print("❌ Erro: Firebase não está conectado!")
            print("💡 Verifique as credenciais do Firebase")
            return
        
        print("✅ Firebase conectado!")
        
        # Limpar Firebase
        print("🗄️ Limpando conversas no Firebase...")
        result = await firebase_service.clear_all_conversations()
        
        if result:
            print("✅ Conversas do Firebase removidas!")
        else:
            print("⚠️ Erro ao limpar Firebase ou nenhuma conversa encontrada")
        
        # Limpar cache local
        print("🧹 Limpando cache de conversas...")
        ai_service = AIService()
        ai_service.clear_conversation_cache()
        print("✅ Cache limpo!")
        
        print("\n🎉 LIMPEZA COMPLETA!")
        print("💡 Agora você pode testar como um lead novo!")
        print("📱 Envie uma mensagem para o WhatsApp para testar")
            
    except Exception as e:
        print(f"❌ Erro durante a limpeza: {str(e)}")

async def clear_specific_conversation(phone_number):
    """Limpa conversa de um número específico"""
    try:
        print(f"🎯 Limpando conversa do número: {phone_number}")
        
        if not firebase_service.check_connection():
            print("❌ Erro: Firebase não está conectado!")
            return
        
        # Limpar do Firebase
        result = await firebase_service.clear_user_conversation(phone_number)
        
        # Limpar do cache
        ai_service = AIService()
        ai_service.clear_conversation_cache(phone_number)
        
        if result:
            print(f"✅ Conversa do {phone_number} removida!")
        else:
            print(f"⚠️ Nenhuma conversa encontrada para {phone_number}")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

def list_users():
    """Lista todos os usuários que já conversaram"""
    try:
        print("👥 Listando usuários com conversas...")
        
        if not firebase_service.check_connection():
            print("❌ Erro: Firebase não está conectado!")
            return
        
        users = firebase_service.list_all_users()
        
        if users:
            print(f"\n📋 Encontrados {len(users)} usuários:")
            for i, user in enumerate(users, 1):
                print(f"   {i}. {user}")
        else:
            print("📭 Nenhum usuário encontrado ou erro na consulta")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

def show_menu():
    """Mostra o menu de opções"""
    print("\n" + "="*60)
    print("🤖 LIMPEZA DE CONVERSAS - SOFIA BOT (ALLEGA IMÓVEIS)")
    print("="*60)
    print("1. 🔥 Limpar TODAS as conversas (Firebase + Cache)")
    print("2. 🎯 Limpar conversa específica")
    print("3. 👥 Listar usuários com conversas")
    print("4. ❌ Sair")
    print("="*60)

async def main():
    """Função principal"""
    print("🤖 Bem-vindo ao limpador de conversas da Sofia!")
    
    while True:
        show_menu()
        choice = input("\nEscolha uma opção (1-4): ").strip()
        
        if choice == "1":
            print("\n⚠️  ATENÇÃO: Esta ação vai remover TODAS as conversas!")
            print("   - Todas as mensagens do Firebase")
            print("   - Todo o cache de conversas")
            print("   - Histórico de todos os usuários")
            
            confirm = input("\n🔸 Tem certeza? Digite 'CONFIRMAR' para continuar: ")
            if confirm.upper() == "CONFIRMAR":
                await clear_all_conversations()
            else:
                print("❌ Operação cancelada!")
                
        elif choice == "2":
            phone = input("\n📱 Digite o número do WhatsApp (ex: 5541999999999): ").strip()
            if phone:
                await clear_specific_conversation(phone)
            else:
                print("❌ Número inválido!")
                
        elif choice == "3":
            list_users()
                
        elif choice == "4":
            print("👋 Saindo... Até logo!")
            break
            
        else:
            print("❌ Opção inválida! Escolha de 1 a 4.")
        
        input("\n⏎ Pressione ENTER para continuar...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa interrompido pelo usuário. Até logo!")
