#!/usr/bin/env python3
"""
Script para Expansão Automática de Dataset Fine-Tuning (Supabase Only)
Uso: python expand_dataset.py [--from-supabase] [--from-csv path.csv] [--augment-factor 3]

Flags:
    --from-supabase     Captura conversas recentes do Supabase (tabela messages + conversations)
    --from-csv arquivo  Importa export de WhatsApp Business em CSV (colunas phone/contact, message, direction, timestamp)
    --augment-factor N  Multiplica dataset via variações sintéticas (default=3)
    --min-examples N    Número mínimo antes de aplicar augmentation/salvar
    --output nome       Prefixo do arquivo de saída (sem extensão)

Notas:
- Conversas são deduplicadas via hash de conteúdo (sem system message)
"""
import asyncio
import argparse
import logging
from pathlib import Path
import sys
import os

# Adicionar diretório do app ao path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.dataset_expander import dataset_expander
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Execução principal do script"""
    
    parser = argparse.ArgumentParser(description='Expandir dataset de fine-tuning')
    parser.add_argument('--from-supabase', action='store_true', 
                       help='Capturar conversas do Supabase (últimos 30 dias)')
    parser.add_argument('--from-csv', type=str, 
                       help='Caminho para export CSV do WhatsApp')
    parser.add_argument('--augment-factor', type=int, default=3,
                       help='Fator de multiplicação para data augmentation')
    parser.add_argument('--output', type=str, 
                       help='Nome do arquivo de saída (opcional)')
    parser.add_argument('--min-examples', type=int, default=50,
                       help='Mínimo de exemplos para prosseguir')
    
    args = parser.parse_args()
    
    logger.info("🚀 Iniciando expansão do dataset de fine-tuning...")
    
    all_examples = []
    
    # 1. Carregar dataset base existente
    if dataset_expander.input_path.exists():
        logger.info(f"📂 Carregando dataset base: {dataset_expander.input_path}")
        base_examples = load_existing_jsonl(dataset_expander.input_path)
        all_examples.extend(base_examples)
        logger.info(f"✅ {len(base_examples)} exemplos base carregados")
    else:
        logger.warning("⚠️ Arquivo base não encontrado, criando dataset do zero")
    
    # 2. Capturar do Supabase (se solicitado)
    if args.from_supabase:
        logger.info("🗄️ Capturando conversas do Supabase...")
        try:
            supabase_examples = await dataset_expander.expand_from_supabase(limit=200)
            all_examples.extend(supabase_examples)
            logger.info(f"✅ {len(supabase_examples)} exemplos capturados do Supabase")
        except Exception as e:
            logger.error(f"❌ Erro ao capturar do Supabase: {e}")
    
    # 3. Carregar CSV do WhatsApp (se fornecido)
    if args.from_csv:
        if Path(args.from_csv).exists():
            logger.info(f"📱 Carregando export WhatsApp: {args.from_csv}")
            csv_examples = dataset_expander.load_whatsapp_export(args.from_csv)
            all_examples.extend(csv_examples)
            logger.info(f"✅ {len(csv_examples)} exemplos carregados do CSV")
        else:
            logger.error(f"❌ Arquivo CSV não encontrado: {args.from_csv}")
    
    # 4. Verificar se temos exemplos suficientes
    if len(all_examples) < args.min_examples:
        logger.error(f"❌ Poucos exemplos encontrados ({len(all_examples)} < {args.min_examples})")
        logger.info("💡 Tente: --from-supabase ou --from-csv arquivo.csv")
        return
    
    logger.info(f"📊 Total de {len(all_examples)} exemplos coletados")
    
    # 5. Aplicar data augmentation
    if args.augment_factor > 1:
        logger.info(f"🔄 Aplicando data augmentation (fator {args.augment_factor})...")
        augmented_examples = await dataset_expander.data_augment_examples(
            all_examples, 
            target_multiplier=args.augment_factor
        )
        logger.info(f"✅ Dataset expandido para {len(augmented_examples)} exemplos")
    else:
        augmented_examples = all_examples
    
    # 6. Salvar dataset final
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"sofia_expanded_{timestamp}"
    
    logger.info(f"💾 Salvando dataset expandido...")
    train_path = dataset_expander.save_expanded_dataset(augmented_examples, output_file)
    
    # 7. Gerar relatório final
    print_final_report(augmented_examples, train_path)
    
    logger.info("🎉 Expansão concluída com sucesso!")

def load_existing_jsonl(file_path: Path) -> list:
    """Carrega exemplos do JSONL existente"""
    from app.services.dataset_expander import TrainingExample
    
    examples = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    messages = data.get('messages', [])
                    
                    if len(messages) >= 2:  # System + pelo menos 1 troca
                        # Calcular lead score baseado no conteúdo
                        full_text = " ".join([m.get('content', '') for m in messages]).lower()
                        lead_score = calculate_simple_lead_score(full_text)
                        has_scheduling = any(
                            keyword in full_text 
                            for keyword in ['visita', 'agendar', 'ver imóvel', 'conhecer']
                        )
                        
                        example = TrainingExample(
                            messages=messages,
                            lead_score=lead_score,
                            has_scheduling=has_scheduling,
                            conversation_id=f"existing_{i}",
                            timestamp=datetime.utcnow(),
                            source="existing_dataset"
                        )
                        examples.append(example)
                
                except json.JSONDecodeError as e:
                    logger.warning(f"Linha {i} inválida no JSONL: {e}")
                except Exception as e:
                    logger.warning(f"Erro na linha {i}: {e}")
    
    except Exception as e:
        logger.error(f"Erro ao carregar {file_path}: {e}")
    
    return examples

def calculate_simple_lead_score(text: str) -> int:
    """Cálculo simples de lead score"""
    score = 1
    
    if any(w in text for w in ['quero', 'procuro', 'interesse']):
        score += 1
    if any(w in text for w in ['quartos', 'metragem', 'área']):
        score += 1
    if any(w in text for w in ['preço', 'valor', 'financiamento']):
        score += 1
    if any(w in text for w in ['visita', 'agendar', 'ver']):
        score += 1
    
    return min(score, 5)

def print_final_report(examples: list, train_path: str):
    """Imprime relatório final"""
    
    # Estatísticas
    total = len(examples)
    by_score = {}
    with_scheduling = 0
    by_source = {}
    
    for ex in examples:
        by_score[ex.lead_score] = by_score.get(ex.lead_score, 0) + 1
        by_source[ex.source] = by_source.get(ex.source, 0) + 1
        if ex.has_scheduling:
            with_scheduling += 1
    
    print("\\n" + "="*60)
    print("📊 RELATÓRIO FINAL DO DATASET")
    print("="*60)
    print(f"📁 Arquivo de treino: {train_path}")
    print(f"📈 Total de exemplos: {total}")
    print(f"🎯 Com agendamento: {with_scheduling} ({with_scheduling/total*100:.1f}%)")
    
    print("\\n📊 Por Lead Score:")
    for score in sorted(by_score.keys()):
        count = by_score[score]
        print(f"   Score {score}: {count:4d} ({count/total*100:.1f}%)")
    
    print("\\n📂 Por Fonte:")
    for source, count in by_source.items():
        print(f"   {source}: {count:4d} ({count/total*100:.1f}%)")
    
    print("\\n🚀 PRÓXIMOS PASSOS:")
    print("1. Instalar OpenAI CLI: pip install openai")
    print("2. Fine-tuning:")
    print(f"   openai api fine_tunes.create \\\\")
    print(f"     -t {train_path} \\\\")
    print(f"     -m gpt-4.1-mini \\\\")
    print(f"     --n_epochs 3 \\\\")
    print(f"     --learning_rate_multiplier 0.3 \\\\")
    print(f"     --batch_size 8")
    
    print("\\n💡 DICAS:")
    if total < 1200:
        print(f"   ⚠️ Considere adicionar mais exemplos (atual: {total}, ideal: 1200+)")
    if with_scheduling/total < 0.6:
        print("   📈 Considere adicionar mais exemplos com agendamento")
    
    print("="*60)

if __name__ == "__main__":
    import json
    asyncio.run(main())