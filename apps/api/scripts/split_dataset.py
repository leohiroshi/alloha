#!/usr/bin/env python3
"""
Split dataset em treino (85%) e validação (15%)
"""

import json
import random
from pathlib import Path

def split_dataset(input_file: str, train_ratio: float = 0.85):
    """Split dataset em treino e validação"""
    
    input_path = Path(input_file)
    
    # Carregar exemplos
    examples = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            examples.append(json.loads(line))
    
    # Shuffle
    random.seed(42)  # Mesmo seed para reproduzibilidade
    random.shuffle(examples)
    
    # Split
    split_idx = int(len(examples) * train_ratio)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]
    
    # Salvar treino
    train_path = input_path.parent / f"{input_path.stem}_train.jsonl"
    with open(train_path, 'w', encoding='utf-8') as f:
        for example in train_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    # Salvar validação
    val_path = input_path.parent / f"{input_path.stem}_val.jsonl"
    with open(val_path, 'w', encoding='utf-8') as f:
        for example in val_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"\n✅ Dataset dividido com sucesso!")
    print(f"   📊 Total: {len(examples)} exemplos")
    print(f"   🎯 Treino: {len(train_examples)} exemplos ({train_ratio*100:.0f}%)")
    print(f"   ✔️  Validação: {len(val_examples)} exemplos ({(1-train_ratio)*100:.0f}%)")
    print(f"\n📁 Arquivos criados:")
    print(f"   {train_path}")
    print(f"   {val_path}")
    print(f"\n🚀 Upload para OpenAI:")
    print(f"   openai api files.create -f {train_path} -p fine-tune")
    print(f"   openai api files.create -f {val_path} -p fine-tune")


if __name__ == "__main__":
    split_dataset("datasets/finetune_dataset_3k.jsonl")
