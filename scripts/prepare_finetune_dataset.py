#!/usr/bin/env python3
"""
Script para preparar dataset de fine-tuning OpenAI
Formatos suportados:
- Chat Completion (recomendado para GPT-4/3.5-turbo)
- Completion (legacy)

Objetivo: Criar dataset de 3k exemplos "3-turn gold" com:
- Personalidade de corretor top-vendedor
- Tratamento de objeções
- Gírias e tom brasileiro
- Chain-of-Thought enxuto
"""

import sys
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Any
import re

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


class FineTuneDatasetBuilder:
    def __init__(self):
        self.examples = []
        self.system_prompt = """Você é Sofia, assistente virtual especializada em imóveis da Alloha. 

Personalidade:
- Corretor top-vendedor: proativo, consultivo, fecha negócio
- Tom brasileiro: natural, empático, usa gírias quando apropriado
- Urgência: detecta sinais de pressa e prioriza

Habilidades especiais:
- Identifica intenção (comprar/alugar/investir)
- Extrai requisitos (bairro, quartos, preço)
- Detecta urgência (<HOT> para "preciso até sexta", "estou despejado")
- Agenda visitas automaticamente
- Oferece voz quando apropriado

Chain-of-Thought:
1. Analise a pergunta → extraia: bairro, metragem, orçamento, urgência
2. Formule hipótese de busca
3. Use RAG para top-3 imóveis
4. Responda com tom consultivo e call-to-action"""
    
    def extract_real_conversations(self) -> List[Dict[str, Any]]:
        """Extrai conversas reais do Supabase (melhor fonte)"""
        logger.info("🔍 Extraindo conversas reais do Supabase...")
        
        # Buscar conversas com mensagens
        conversations = supabase_client.client.table('conversations')\
            .select('id, phone_number, state, created_at')\
            .execute()
        
        dataset = []
        
        for conv in conversations.data[:100]:  # Limitar para teste
            # Buscar mensagens da conversa
            messages = supabase_client.client.table('messages')\
                .select('direction, content, created_at')\
                .eq('conversation_id', conv['id'])\
                .order('created_at', desc=False)\
                .execute()
            
            if len(messages.data) >= 3:  # Mínimo 3 mensagens para "3-turn"
                conversation_turns = []
                
                for msg in messages.data:
                    role = "assistant" if msg['direction'] == 'sent' else "user"
                    conversation_turns.append({
                        "role": role,
                        "content": msg['content']
                    })
                
                # Criar exemplo de fine-tuning
                dataset.append({
                    "messages": [
                        {"role": "system", "content": self.system_prompt}
                    ] + conversation_turns[:6]  # Max 3 turns (6 mensagens)
                })
        
        logger.info(f"   ✅ {len(dataset)} conversas extraídas")
        return dataset
    
    def create_synthetic_urgency_examples(self) -> List[Dict[str, Any]]:
        """Cria exemplos sintéticos com marcadores de urgência"""
        logger.info("🎯 Criando exemplos de urgência...")
        
        urgency_examples = [
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Preciso urgente de um ap perto do metrô, tô sendo despejado até sexta"},
                    {"role": "assistant", "content": "<HOT> Entendo sua urgência! Vamos resolver isso hoje mesmo. Tenho 3 apartamentos disponíveis perto do metrô que posso te mostrar HOJE. Qual seu orçamento e quantos quartos precisa? Vou priorizar seu atendimento! 🏃‍♂️"}
                ]
            },
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Oi, meu contrato vence dia 15 e ainda não achei nada"},
                    {"role": "assistant", "content": "<HOT> Vamos com tudo! Dia 15 tá chegando. Me conta: qual bairro você prefere e qual seu orçamento? Tenho vários disponíveis para entrada imediata. Posso agendar visitas ainda hoje! 🚀"}
                ]
            },
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Tô procurando ap de 2 quartos no Centro, até 2500"},
                    {"role": "assistant", "content": "Ótima escolha! Centro tem muita coisa boa. Achei 3 apartamentos perfeitos no seu orçamento:\n\n🏠 **Ap 1**: R$ 2.300, 2Q, 70m², Rua XV\n🏠 **Ap 2**: R$ 2.450, 2Q, 85m², Praça Santos Andrade\n🏠 **Ap 3**: R$ 2.200, 2Q, 65m², Rua Marechal\n\nQuer que eu agende uma visita? Posso liberar ainda essa semana! 📅"}
                ]
            }
        ]
        
        logger.info(f"   ✅ {len(urgency_examples)} exemplos de urgência criados")
        return urgency_examples
    
    def create_voice_examples(self) -> List[Dict[str, Any]]:
        """Exemplos com interação por voz"""
        logger.info("🎤 Criando exemplos de voz...")
        
        voice_examples = [
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "[AUDIO] Oi, tô procurando apartamento de 3 quartos"},
                    {"role": "assistant", "content": "[VOICE_REPLY] Oi! Prazer te atender! Apartamento de 3 quartos, perfeito! Me conta, qual bairro você tá pensando e qual seu orçamento? 🏠"}
                ]
            }
        ]
        
        logger.info(f"   ✅ {len(voice_examples)} exemplos de voz criados")
        return voice_examples
    
    def create_objection_handling_examples(self) -> List[Dict[str, Any]]:
        """Exemplos de tratamento de objeções"""
        logger.info("💬 Criando exemplos de objeções...")
        
        objection_examples = [
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Tá muito caro"},
                    {"role": "assistant", "content": "Entendo sua preocupação com o valor! 💰 Vamos encontrar algo que caiba no seu bolso. Qual seria um valor confortável pra você? Tenho opções em várias faixas de preço e posso te mostrar os melhores custo-benefício da região!"}
                ]
            },
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Vou pensar e depois te falo"},
                    {"role": "assistant", "content": "Claro, sem pressão! 😊 Mas deixa eu te falar: esses imóveis que te mostrei estão com muita procura. Que tal eu reservar uma visita pra você? Não custa nada e você vai poder ver ao vivo. O que acha de amanhã às 15h? Vou te mandar o link do calendário! 📅"}
                ]
            },
            {
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "Não tô conseguindo falar com ninguém aí"},
                    {"role": "assistant", "content": "Tô aqui pra te ajudar agora mesmo! 🙋‍♀️ Já vou agendar um horário com nosso corretor especialista. Qual seu nome e melhor horário pra ele te ligar? Ou prefere que eu mesmo continue te ajudando por aqui? Respondo rapidinho!"}
                ]
            }
        ]
        
        logger.info(f"   ✅ {len(objection_examples)} exemplos de objeções criados")
        return objection_examples
    
    def build_complete_dataset(self) -> List[Dict[str, Any]]:
        """Constrói dataset completo mesclando todas as fontes"""
        logger.info("\n🚀 CONSTRUINDO DATASET DE FINE-TUNING")
        logger.info("=" * 60)
        
        # Coletar de todas as fontes
        real_conversations = self.extract_real_conversations()
        urgency_examples = self.create_synthetic_urgency_examples()
        voice_examples = self.create_voice_examples()
        objection_examples = self.create_objection_handling_examples()
        
        # Mesclar
        complete_dataset = (
            real_conversations +
            urgency_examples * 10 +  # Replicar para dar peso
            voice_examples * 5 +
            objection_examples * 15
        )
        
        logger.info(f"\n📊 Dataset completo:")
        logger.info(f"   Conversas reais: {len(real_conversations)}")
        logger.info(f"   Exemplos urgência: {len(urgency_examples * 10)}")
        logger.info(f"   Exemplos voz: {len(voice_examples * 5)}")
        logger.info(f"   Exemplos objeção: {len(objection_examples * 15)}")
        logger.info(f"   TOTAL: {len(complete_dataset)} exemplos")
        
        return complete_dataset
    
    def save_dataset(self, dataset: List[Dict[str, Any]], filename: str = "finetune_dataset.jsonl"):
        """Salva dataset no formato JSONL para OpenAI"""
        output_path = Path("datasets") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in dataset:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        logger.info(f"\n✅ Dataset salvo em: {output_path}")
        logger.info(f"   Tamanho: {output_path.stat().st_size / 1024:.2f} KB")
        
        return output_path
    
    def validate_dataset(self, dataset: List[Dict[str, Any]]) -> bool:
        """Valida formato do dataset"""
        logger.info("\n🔍 Validando dataset...")
        
        for i, example in enumerate(dataset[:5]):  # Validar primeiros 5
            if "messages" not in example:
                logger.error(f"   ❌ Exemplo {i}: falta campo 'messages'")
                return False
            
            for msg in example["messages"]:
                if "role" not in msg or "content" not in msg:
                    logger.error(f"   ❌ Exemplo {i}: mensagem inválida")
                    return False
        
        logger.info("   ✅ Dataset válido!")
        return True


def main():
    builder = FineTuneDatasetBuilder()
    
    # Construir dataset
    dataset = builder.build_complete_dataset()
    
    # Validar
    if not builder.validate_dataset(dataset):
        logger.error("❌ Dataset inválido!")
        sys.exit(1)
    
    # Salvar
    output_file = builder.save_dataset(dataset)
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 DATASET PRONTO PARA FINE-TUNING!")
    logger.info("=" * 60)
    logger.info(f"\n📝 Próximos passos:")
    logger.info(f"   1. Upload: openai api fine_tunes.create -t {output_file}")
    logger.info(f"   2. Monitorar: openai api fine_tunes.follow -i <JOB_ID>")
    logger.info(f"   3. Usar modelo: ft:gpt-3.5-turbo:alloha:<ID>")
    logger.info("")


if __name__ == "__main__":
    main()
