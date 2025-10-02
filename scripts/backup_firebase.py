#!/usr/bin/env python3
"""
Backup completo do Firebase antes da migração
Gera arquivos JSON com todos os dados
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List

# Adicionar o diretório raiz ao path para importar módulos app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.firebase_service import firebase_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FirebaseBackup:
    """Backup completo do Firebase"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
    def backup_collection(self, collection_name: str) -> List[Dict]:
        """Faz backup de uma coleção completa"""
        logger.info(f"📦 Fazendo backup de '{collection_name}'...")
        
        try:
            docs_ref = firebase_service.db.collection(collection_name).stream()
            
            documents = []
            count = 0
            
            for doc in docs_ref:
                doc_data = doc.to_dict()
                doc_data['_id'] = doc.id  # Preservar ID original
                
                # Converter timestamps para string
                for key, value in doc_data.items():
                    if hasattr(value, 'isoformat'):
                        doc_data[key] = value.isoformat()
                
                documents.append(doc_data)
                count += 1
                
                if count % 100 == 0:
                    logger.info(f"   Processados: {count}")
            
            logger.info(f"✅ {count} documentos salvos de '{collection_name}'")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer backup de '{collection_name}': {e}")
            return []
    
    def save_backup(self, collection_name: str, data: List[Dict]):
        """Salva backup em arquivo JSON"""
        filename = f"backup_{collection_name}_{self.timestamp}.json"
        filepath = self.backup_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            file_size = filepath.stat().st_size / 1024 / 1024  # MB
            logger.info(f"💾 Backup salvo: {filename} ({file_size:.2f} MB)")
            
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar backup: {e}")
            return None
    
    def run_full_backup(self) -> Dict[str, str]:
        """Executa backup completo de todas as coleções"""
        logger.info("="*60)
        logger.info("🚀 INICIANDO BACKUP COMPLETO DO FIREBASE")
        logger.info("="*60)
        
        collections_to_backup = [
            'properties',
            'conversations', 
            'messages',
            'leads',
            'urgency_alerts',
            'scheduled_visits',
            'voice_interactions',
            'white_label_sites'
        ]
        
        backups = {}
        
        for collection in collections_to_backup:
            logger.info(f"\n📁 Coleção: {collection}")
            
            # Fazer backup
            data = self.backup_collection(collection)
            
            if data:
                # Salvar arquivo
                filepath = self.save_backup(collection, data)
                if filepath:
                    backups[collection] = filepath
        
        # Criar arquivo de manifesto
        manifest = {
            'backup_date': datetime.utcnow().isoformat(),
            'timestamp': self.timestamp,
            'collections': {
                name: len(self.backup_collection(name)) 
                for name in collections_to_backup
            },
            'files': backups
        }
        
        manifest_file = self.backup_dir / f"backup_manifest_{self.timestamp}.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info("\n" + "="*60)
        logger.info("✅ BACKUP COMPLETO FINALIZADO!")
        logger.info("="*60)
        logger.info(f"\n📋 Manifesto: {manifest_file}")
        logger.info(f"📁 Diretório: {self.backup_dir}")
        logger.info(f"\n📊 Estatísticas:")
        
        total_docs = sum(manifest['collections'].values())
        logger.info(f"   Total documentos: {total_docs:,}")
        logger.info(f"   Total coleções: {len(backups)}")
        
        # Tamanho total
        total_size = sum(
            Path(filepath).stat().st_size 
            for filepath in backups.values()
        ) / 1024 / 1024
        logger.info(f"   Tamanho total: {total_size:.2f} MB")
        
        return backups

def main():
    """Executa backup"""
    backup = FirebaseBackup()
    backups = backup.run_full_backup()
    
    if len(backups) > 0:
        print("\n✅ Backup concluído com sucesso!")
        print(f"📁 Arquivos salvos em: {backup.backup_dir}")
        print("\n⚠️  IMPORTANTE: Guarde esses backups em local seguro!")
        return 0
    else:
        print("\n❌ Backup falhou!")
        return 1

if __name__ == "__main__":
    exit(main())
