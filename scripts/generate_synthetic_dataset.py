#!/usr/bin/env python3
"""
Gerador de Dataset Sintético de Alta Qualidade para Fine-Tuning
Meta: 3000+ exemplos realistas baseados em padrões brasileiros
"""

import json
import random
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class SyntheticDatasetGenerator:
    def __init__(self):
        # Sistema prompt padrão
        self.system_prompt = "Você é Sofia, assistente virtual especializada em imóveis da Alloha. Seja profissional, simpática e direta."
        
        # Variações realistas brasileiras
        self.greetings = [
            "Oi", "Olá", "Oi!", "Olá!", "Bom dia", "Boa tarde", "Boa noite",
            "E aí", "Opa", "Fala", "oii", "oie", "olaa", "Oii", "ola",
            "oi tudo bem", "ola tudo bom", "oi Sofia", "bom dia Sofia"
        ]
        
        self.interests = [
            "quero alugar um apartamento", "procuro apartamento", "tô procurando imóvel",
            "preciso de um apto", "gostaria de alugar", "to interessado em alugar",
            "tenho interesse em imóveis", "busco apartamento", "queria ver opções",
            "vc tem apartamento disponível", "tem algum disponível", "quero ver imóveis",
            "estou procurando lugar", "preciso achar um ap", "queria alugar"
        ]
        
        self.neighborhoods = [
            "centro", "batel", "água verde", "bigorrilho", "juvevê", "cabral",
            "alto da glória", "portão", "champagnat", "ecoville", "rebouças",
            "cristo rei", "santa felicidade", "boa vista", "jardim social"
        ]
        
        self.features = [
            "2 quartos", "3 quartos", "1 quarto", "2 dormitórios", "3 dorm",
            "com vaga", "com garagem", "vaga coberta", "2 vagas", "sem vaga",
            "mobiliado", "semi mobiliado", "com móveis", "vazio", "decorado",
            "pet friendly", "aceita pet", "permite cachorro", "aceita animais",
            "varanda", "sacada", "churrasqueira", "área de lazer", "piscina"
        ]
        
        self.price_ranges = [
            "até R$ 1500", "até R$ 2000", "até 2 mil", "menos de 3000",
            "entre 1500 e 2500", "até 3500", "máximo 4000", "preço bom"
        ]
        
        self.urgency_phrases = [
            "preciso urgente", "é urgente", "preciso pra ontem", "preciso até sexta",
            "estou sendo despejado", "mudança urgente", "preciso mudar logo",
            "é pra semana que vem", "sem tempo", "rapidão", "pra agora", "pra hoje",
            "contrato acabando", "tô sem lugar", "preciso com urgência", "pra já"
        ]
        
        self.objections = [
            ("tá muito caro", "Entendo sua preocupação com o valor. Temos opções em diferentes faixas. Qual seria o valor ideal para você?"),
            ("é longe", "A localização é importante! Qual região seria mais conveniente? Trabalha ou estuda em algum bairro?"),
            ("não aceita pet", "Você tem pet! Temos várias opções pet friendly. Me conta sobre seu bichinho?"),
            ("muito pequeno", "Precisa de mais espaço! Quantos quartos seriam ideais? Qual metragem você considera confortável?"),
            ("vou pensar", "Claro! Enquanto isso posso te enviar mais opções para comparar. Qual seria o prazo de decisão?"),
            ("outro dia eu vejo", "Sem pressa! Posso salvar essas opções. Quando seria um bom momento para retomarmos?"),
            ("só tô olhando", "Ótimo começar pesquisando! Posso te ajudar a entender o mercado. Quando pretende mudar?"),
            ("não gostei", "Entendo! Me conta o que não agradou? Assim encontro algo mais no seu perfil."),
            ("tem mais barato?", "Sim! Temos opções variadas. Qual faixa de preço funciona melhor?"),
            ("mt caro", "Entendo! Qual faixa de preço você está considerando?"),
            ("eh longe", "Qual região seria melhor para você?"),
            ("nao gostei", "O que não agradou? Posso buscar outras opções."),
            ("vou ver", "Tranquilo! Quer que eu envie mais opções enquanto você pensa?")
        ]
        
        self.typo_replacements = [
            ("você", "vc"), ("está", "tá"), ("para", "pra"), ("porque", "pq"),
            ("também", "tb"), ("muito", "mt"), ("não", "nao"), ("mais", "mas"),
            ("obrigado", "obg"), ("aluguel", "alugel"), ("apartamento", "ap"),
            ("quero", "kero"), ("banheiro", "banhero"), ("quarto", "kuarto")
        ]
        
        self.examples = []
    
    def generate_basic_inquiry(self, count: int = 500):
        """Gera consultas básicas variadas"""
        logger.info(f"🔹 Gerando {count} consultas básicas...")
        
        for _ in range(count):
            greeting = random.choice(self.greetings)
            interest = random.choice(self.interests)
            neighborhood = random.choice(self.neighborhoods)
            feature = random.choice(self.features)
            
            user_msg = f"{greeting}, {interest} {feature} em {neighborhood}"
            
            # 30% chance de adicionar preço
            if random.random() < 0.3:
                user_msg += f", {random.choice(self.price_ranges)}"
            
            # Aplicar typos ocasionalmente
            if random.random() < 0.4:
                user_msg = self._apply_typos(user_msg)
            
            assistant_msg = f"Oi! Que bom ter você aqui! Você busca {feature} em {neighborhood}. Vou buscar as melhores opções para você! 🏠"
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ]
            })
    
    def generate_urgency_cases(self, count: int = 400):
        """Gera casos com urgência"""
        logger.info(f"🔥 Gerando {count} casos de urgência...")
        
        for _ in range(count):
            urgency = random.choice(self.urgency_phrases)
            feature = random.choice(self.features)
            neighborhood = random.choice(self.neighborhoods)
            
            user_msg = f"{urgency}, {random.choice(self.interests)} {feature} em {neighborhood}"
            
            assistant_msg = f"<HOT> Entendo a urgência! Vou priorizar sua busca. {feature} em {neighborhood} - buscando opções disponíveis AGORA! ⚡"
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ]
            })
    
    def generate_voice_messages(self, count: int = 300):
        """Gera respostas a mensagens de voz"""
        logger.info(f"🎤 Gerando {count} mensagens de voz...")
        
        voice_indicators = ["[Áudio]", "[PTT]", "[Mensagem de voz]", "🎤", "[voz]", "áudio:"]
        
        for _ in range(count):
            indicator = random.choice(voice_indicators)
            neighborhood = random.choice(self.neighborhoods)
            feature = random.choice(self.features)
            
            user_msg = f"{indicator} {random.choice(self.greetings)}, {random.choice(self.interests)} {feature} em {neighborhood}"
            
            assistant_msg = f"[VOICE_REPLY] Oi! Entendi perfeitamente seu áudio! Você busca {feature} em {neighborhood}. Vou te enviar opções agora! 🎧"
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ]
            })
    
    def generate_objection_handling(self, count: int = 600):
        """Gera manejo de objeções"""
        logger.info(f"💬 Gerando {count} objeções...")
        
        for _ in range(count):
            objection, response = random.choice(self.objections)
            
            # Variação com typos
            if random.random() < 0.5:
                objection = self._apply_typos(objection)
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": objection},
                    {"role": "assistant", "content": response}
                ]
            })
    
    def generate_followup_scheduling(self, count: int = 400):
        """Gera agendamentos de visita"""
        logger.info(f"📅 Gerando {count} agendamentos...")
        
        scheduling_requests = [
            "quero visitar", "posso ver?", "quando posso ir?", "quero agendar",
            "gostei! quero ver", "pode marcar visita?", "tem horário?",
            "quero conhecer", "posso ir ver amanhã?", "disponível sábado?"
        ]
        
        for _ in range(count):
            user_msg = random.choice(scheduling_requests)
            
            assistant_msg = "[SCHEDULE_VISIT] Ótimo! Vou agendar sua visita. Qual dia e horário funciona melhor? Manhã ou tarde? 📅"
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ]
            })
    
    def generate_price_inquiries(self, count: int = 300):
        """Gera consultas de preço"""
        logger.info(f"💰 Gerando {count} consultas de preço...")
        
        price_questions = [
            "quanto custa?", "qual o valor?", "quanto é?", "preço?",
            "quanto tá?", "valor do aluguel?", "qnto custa esse?",
            "qnt eh", "vlr?", "preço desse"
        ]
        
        for _ in range(count):
            user_msg = random.choice(price_questions)
            
            assistant_msg = "[CHECK_PRICE] Deixe-me consultar o valor atualizado para você... 💰"
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg}
                ]
            })
    
    def generate_multi_turn_conversations(self, count: int = 400):
        """Gera conversas com múltiplos turnos"""
        logger.info(f"💭 Gerando {count} conversas completas...")
        
        for _ in range(count):
            neighborhood = random.choice(self.neighborhoods)
            feature = random.choice(self.features)
            price = random.choice(self.price_ranges)
            
            # Turno 1: Interesse inicial
            user1 = f"{random.choice(self.greetings)}, {random.choice(self.interests)}"
            assistant1 = "Oi! Que bom ter você aqui! Me conta, que tipo de imóvel você procura?"
            
            # Turno 2: Especificação
            user2 = f"{feature} em {neighborhood}, {price}"
            assistant2 = f"Perfeito! {feature} em {neighborhood}, {price}. Deixa eu buscar as melhores opções! 🔍"
            
            # Turno 3: Interesse em visitar
            user3 = random.choice(["gostei!", "legal!", "quero ver", "tem foto?"])
            assistant3 = "Ótimo! Vou te enviar fotos e detalhes agora. Posso agendar uma visita para você também! 📸"
            
            self.examples.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user1},
                    {"role": "assistant", "content": assistant1},
                    {"role": "user", "content": user2},
                    {"role": "assistant", "content": assistant2},
                    {"role": "user", "content": user3},
                    {"role": "assistant", "content": assistant3}
                ]
            })
    
    def _apply_typos(self, text: str) -> str:
        """Aplica typos realistas"""
        for original, typo in random.sample(self.typo_replacements, k=min(2, len(self.typo_replacements))):
            if original in text.lower():
                text = text.replace(original, typo)
        return text
    
    def generate_full_dataset(self):
        """Gera dataset completo"""
        logger.info("\n" + "="*60)
        logger.info("🚀 GERANDO DATASET SINTÉTICO DE ALTA QUALIDADE")
        logger.info("="*60 + "\n")
        
        self.generate_basic_inquiry(500)
        self.generate_urgency_cases(400)
        self.generate_voice_messages(300)
        self.generate_objection_handling(600)
        self.generate_followup_scheduling(400)
        self.generate_price_inquiries(300)
        self.generate_multi_turn_conversations(400)
        
        # Shuffle
        random.shuffle(self.examples)
        
        logger.info("\n" + "="*60)
        logger.info(f"✅ DATASET COMPLETO: {len(self.examples)} exemplos")
        logger.info("="*60 + "\n")
        
        return self.examples
    
    def save_dataset(self, filename: str = "finetune_dataset_3k.jsonl"):
        """Salva dataset em JSONL"""
        output_path = Path("datasets") / filename
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in self.examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        size_kb = output_path.stat().st_size / 1024
        
        logger.info(f"💾 Dataset salvo: {output_path}")
        logger.info(f"📊 Total: {len(self.examples)} exemplos")
        logger.info(f"📦 Tamanho: {size_kb:.2f} KB")
        logger.info(f"\n✅ Pronto para upload!")
        logger.info(f"   openai api files.create -f {output_path} -p fine-tune")


def main():
    generator = SyntheticDatasetGenerator()
    generator.generate_full_dataset()
    generator.save_dataset()


if __name__ == "__main__":
    main()
