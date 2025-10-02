#!/usr/bin/env python3
"""
Script de limpeza pós-migração
Remove arquivos de teste, migração e temporários
Mantém apenas arquivos essenciais para produção
"""

import os
import shutil
from pathlib import Path

# Diretório raiz do projeto
ROOT = Path(__file__).parent.parent

print("🧹 LIMPEZA PÓS-MIGRAÇÃO")
print("=" * 60)

# Arquivos e diretórios a REMOVER
to_remove = [
    # Scripts de migração (já usados)
    "scripts/migrate_properties.py",
    "scripts/migrate_conversations.py",
    "scripts/migrate_conversations_v2.py",
    "scripts/retry_failed_properties.py",
    "scripts/cleanup_and_remigrate.py",
    
    # Scripts de validação e teste
    "scripts/validate_migration.py",
    "scripts/test_supabase_queries.py",
    "scripts/load_test_supabase.py",
    "scripts/test_price_conversion.py",
    
    # Scripts de inspeção
    "scripts/inspect_firebase_structure.py",
    "scripts/inspect_conversations_structure.py",
    "scripts/check_supabase_tables.py",
    
    # SQL temporários
    "scripts/fix_embedding_dimension.sql",
    "scripts/fix_hybrid_search_function.sql",
    
    # Backups antigos (manter apenas os mais recentes)
    "backups/",
    
    # Logs de falha (já corrigidos)
    "logs/failed_*.json",
    
    # ChromaDB (não usamos mais, migramos para Supabase)
    "chroma_db/",
    
    # Datasets expandidos (temporários)
    "datasets/expanded/",
    
    # CSV de teste
    "allega_imoveis_selenium.csv",
    
    # Firestore rules (não usamos mais)
    "firestore.rules",
    
    # Guia de migração (já concluído)
    "MIGRATION_GUIDE.md",
    
    # Arquivos de modelo antigo
    "unsloth.Q8_0.gguf",
    "Modelfile",
    
    # Logs de pipeline
    "rag_pipeline.log",
    
    # Cache Python
    "scripts/__pycache__/",
    "__pycache__/",
]

# Arquivos a MANTER
keep_files = [
    "scripts/backup_firebase.py",  # Útil para backups futuros
    "scripts/supabase_schema.sql",  # Schema de referência
    "scripts/checkpoint_72h.py",  # Checkpoint útil
    "scripts/expand_dataset.py",  # Dataset expansion
    "scripts/restore_firestore_schema.py",  # Caso precise voltar ao Firebase
    "app/",  # Código da aplicação
    "requirements.txt",
    "README.md",
    "Dockerfile",
    ".env",
    ".env.example",
    ".gitignore",
]

removed_count = 0
kept_count = 0
errors = []

print("\n📋 Arquivos que serão removidos:\n")

for item in to_remove:
    path = ROOT / item
    
    # Verificar se existe
    if not path.exists():
        # Verificar wildcard
        if '*' in item:
            parent = path.parent
            pattern = path.name
            if parent.exists():
                matches = list(parent.glob(pattern))
                for match in matches:
                    print(f"   🗑️  {match.relative_to(ROOT)}")
        continue
    
    print(f"   🗑️  {item}")

print("\n" + "=" * 60)
confirm = input("\n⚠️  Confirma remoção destes arquivos? (s/N): ")

if confirm.lower() != 's':
    print("\n❌ Operação cancelada pelo usuário")
    exit(0)

print("\n🚀 Removendo arquivos...\n")

for item in to_remove:
    path = ROOT / item
    
    try:
        # Verificar wildcard
        if '*' in item:
            parent = path.parent
            pattern = path.name
            if parent.exists():
                matches = list(parent.glob(pattern))
                for match in matches:
                    if match.is_file():
                        match.unlink()
                        print(f"   ✅ Removido: {match.relative_to(ROOT)}")
                        removed_count += 1
                    elif match.is_dir():
                        shutil.rmtree(match)
                        print(f"   ✅ Removido: {match.relative_to(ROOT)}/")
                        removed_count += 1
            continue
        
        if not path.exists():
            continue
        
        if path.is_file():
            path.unlink()
            print(f"   ✅ Removido: {item}")
            removed_count += 1
        elif path.is_dir():
            shutil.rmtree(path)
            print(f"   ✅ Removido: {item}/")
            removed_count += 1
    
    except Exception as e:
        errors.append(f"{item}: {e}")
        print(f"   ❌ Erro ao remover {item}: {e}")

print("\n" + "=" * 60)
print("📊 RESUMO DA LIMPEZA")
print("=" * 60)
print(f"\n✅ Arquivos removidos: {removed_count}")
print(f"❌ Erros: {len(errors)}")

if errors:
    print("\n❌ Erros encontrados:")
    for error in errors:
        print(f"   - {error}")

print("\n✅ Arquivos mantidos para produção:")
for item in keep_files:
    path = ROOT / item
    if path.exists():
        if path.is_dir():
            print(f"   📁 {item}/")
        else:
            print(f"   📄 {item}")

print("\n" + "=" * 60)
print("✅ LIMPEZA CONCLUÍDA!")
print("\n💡 Próximos passos:")
print("   1. Atualizar .env: USE_SUPABASE=true")
print("   2. Commit das mudanças: git add . && git commit -m 'cleanup: remove migration files'")
print("   3. Deploy para produção")
