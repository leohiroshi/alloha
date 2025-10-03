#!/usr/bin/env python3
"""
Script de Limpeza de Propriedades Antigas - Supabase
Remove ou desativa propriedades com updated_at > 6h para garantir frescor do RAG
"""

import sys
from pathlib import Path
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.supabase_client import supabase_client
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PropertyCleaner:
    """Limpa propriedades antigas do Supabase"""
    
    def __init__(self, hours_threshold: int = 6):
        self.hours_threshold = hours_threshold
        self.stats = {
            'total_active': 0,
            'total_old': 0,
            'deactivated': 0,
            'csv_exported': False,
            'errors': []
        }
    
    def get_old_properties(self) -> List[Dict[str, Any]]:
        """Busca propriedades ativas com updated_at > threshold"""
        logger.info(f"🔍 Buscando propriedades com updated_at > {self.hours_threshold}h...")
        
        # Calcular timestamp threshold
        threshold = datetime.utcnow() - timedelta(hours=self.hours_threshold)
        threshold_iso = threshold.isoformat()
        
        logger.info(f"   Threshold: {threshold_iso}")
        
        # Buscar propriedades antigas E ativas
        result = supabase_client.client.table('properties')\
            .select('property_id, title, price, updated_at, status')\
            .eq('status', 'active')\
            .lt('updated_at', threshold_iso)\
            .execute()
        
        old_properties = result.data
        self.stats['total_old'] = len(old_properties)
        
        logger.info(f"   ⚠️ Encontradas: {len(old_properties)} propriedades antigas")
        
        return old_properties
    
    def get_active_properties(self) -> List[Dict[str, Any]]:
        """Busca todas as propriedades ativas (para CSV)"""
        logger.info("📊 Buscando propriedades ativas...")
        
        result = supabase_client.client.table('properties')\
            .select('property_id, title, price, bedrooms, bathrooms, area_m2, property_type, status, updated_at, created_at')\
            .eq('status', 'active')\
            .order('updated_at', desc=True)\
            .execute()
        
        active_properties = result.data
        self.stats['total_active'] = len(active_properties)
        
        logger.info(f"   ✅ {len(active_properties)} propriedades ativas")
        
        return active_properties
    
    def export_active_to_csv(self, properties: List[Dict[str, Any]]) -> Path:
        """Exporta propriedades ativas para CSV"""
        logger.info("💾 Exportando CSV de propriedades ativas...")
        
        # Criar diretório datasets se não existir
        datasets_dir = Path("datasets")
        datasets_dir.mkdir(exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = datasets_dir / f"active_properties_{timestamp}.csv"
        
        # Escrever CSV
        if properties:
            fieldnames = properties[0].keys()
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(properties)
            
            file_size = csv_path.stat().st_size / 1024
            logger.info(f"   ✅ CSV exportado: {csv_path}")
            logger.info(f"   📏 Tamanho: {file_size:.2f} KB")
            logger.info(f"   📊 Linhas: {len(properties)}")
            
            self.stats['csv_exported'] = True
        else:
            logger.warning("   ⚠️ Nenhuma propriedade para exportar")
        
        return csv_path
    
    def deactivate_old_properties(self, properties: List[Dict[str, Any]], dry_run: bool = False) -> int:
        """Desativa propriedades antigas (não deleta)"""
        if not properties:
            logger.info("✅ Nenhuma propriedade antiga para desativar")
            return 0
        
        if dry_run:
            logger.info(f"🔍 DRY RUN - {len(properties)} propriedades seriam desativadas:")
            for prop in properties[:10]:  # Mostrar só as primeiras 10
                logger.info(f"   - {prop['property_id']}: {prop['title'][:50]}... (updated: {prop['updated_at']})")
            
            if len(properties) > 10:
                logger.info(f"   ... e mais {len(properties) - 10} propriedades")
            
            return 0
        
        logger.info(f"🧹 Desativando {len(properties)} propriedades antigas...")
        
        deactivated = 0
        
        for prop in properties:
            try:
                # UPDATE: status = 'inactive'
                result = supabase_client.client.table('properties')\
                    .update({
                        'status': 'inactive',
                        'updated_at': datetime.utcnow().isoformat()
                    })\
                    .eq('property_id', prop['property_id'])\
                    .execute()
                
                if result.data:
                    deactivated += 1
                    
                    if deactivated % 10 == 0:
                        logger.info(f"   Desativadas: {deactivated}/{len(properties)}")
            
            except Exception as e:
                error_msg = f"Erro ao desativar {prop['property_id']}: {e}"
                logger.error(f"   ❌ {error_msg}")
                self.stats['errors'].append(error_msg)
        
        self.stats['deactivated'] = deactivated
        logger.info(f"   ✅ {deactivated}/{len(properties)} propriedades desativadas")
        
        return deactivated
    
    def print_summary(self):
        """Imprime resumo da operação"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 RESUMO DA LIMPEZA DE PROPRIEDADES")
        logger.info("=" * 70)
        
        logger.info(f"\n📈 Estatísticas:")
        logger.info(f"   Total de propriedades ativas: {self.stats['total_active']}")
        logger.info(f"   Total de propriedades antigas: {self.stats['total_old']}")
        logger.info(f"   Propriedades desativadas: {self.stats['deactivated']}")
        
        logger.info(f"\n💾 Exportação:")
        logger.info(f"   CSV exportado: {'✅' if self.stats['csv_exported'] else '❌'}")
        
        if self.stats['errors']:
            logger.info(f"\n⚠️ Erros ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:
                logger.info(f"   - {error}")
            
            if len(self.stats['errors']) > 5:
                logger.info(f"   ... e mais {len(self.stats['errors']) - 5} erros")
        
        logger.info("\n" + "=" * 70)
        
        # Recomendações
        if self.stats['total_old'] > 0 and self.stats['deactivated'] == 0:
            logger.info("💡 Execute novamente SEM --dry-run para aplicar as alterações")
        elif self.stats['deactivated'] > 0:
            logger.info("✅ Limpeza concluída! RAG agora tem apenas propriedades frescas")
    
    def run(self, dry_run: bool = False):
        """Executa limpeza completa"""
        logger.info("🚀 INICIANDO LIMPEZA DE PROPRIEDADES ANTIGAS")
        logger.info("=" * 70)
        logger.info(f"Threshold: {self.hours_threshold} horas")
        logger.info(f"Modo: {'DRY RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
        logger.info("")
        
        # 1. Buscar propriedades ativas (para CSV)
        active_properties = self.get_active_properties()
        
        # 2. Exportar CSV
        if active_properties:
            self.export_active_to_csv(active_properties)
        
        # 3. Buscar propriedades antigas
        old_properties = self.get_old_properties()
        
        # 4. Desativar propriedades antigas
        if old_properties:
            self.deactivate_old_properties(old_properties, dry_run=dry_run)
        
        # 5. Resumo
        self.print_summary()
        
        return self.stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpa propriedades antigas do Supabase')
    parser.add_argument(
        '--hours',
        type=int,
        default=6,
        help='Threshold em horas (padrão: 6)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula a limpeza sem aplicar alterações'
    )
    
    args = parser.parse_args()
    
    # Executar limpeza
    cleaner = PropertyCleaner(hours_threshold=args.hours)
    stats = cleaner.run(dry_run=args.dry_run)
    
    # Exit code
    if stats['errors']:
        logger.error("\n❌ Limpeza concluída com erros")
        sys.exit(1)
    else:
        logger.info("\n✅ Limpeza concluída com sucesso!")
        sys.exit(0)


if __name__ == "__main__":
    main()
