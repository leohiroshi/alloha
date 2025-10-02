"""
Sistema de Captura e Expansão Automática de Dataset para Fine-Tuning
Transforma conversas reais em exemplos de treinamento otimizados
"""
import json
import re
import pandas as pd
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
import random
import hashlib
import os
from dataclasses import dataclass

# Para data augmentation
try:
    from googletrans import Translator
except ImportError:
    Translator = None

logger = logging.getLogger(__name__)

@dataclass
class TrainingExample:
    """Estrutura de um exemplo de treinamento"""
    messages: List[Dict[str, str]]
    lead_score: int  # 1-5
    has_scheduling: bool
    conversation_id: str
    timestamp: datetime
    source: str  # "firebase", "whatsapp_export", "manual"

class DatasetExpander:
    """Expandir dataset de fine-tuning automaticamente"""
    
    def __init__(self, 
                 input_jsonl_path: str = "sofia_training_data.jsonl",
                 output_dir: str = "datasets/expanded"):
        
        self.input_path = Path(input_jsonl_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache para evitar duplicatas
        self.seen_conversations = set()
        
        # Padrões para análise
        self.scheduling_patterns = [
            r'(visita|agend|chave|sábado|domingo|\d{1,2}\/\d{1,2})',
            r'(segunda|terça|quarta|quinta|sexta|fim de semana)',
            r'(\d{1,2}:\d{2}|\d{1,2}h\d{0,2}|manhã|tarde|noite)',
            r'(posso|podemos|vamos) (ver|visitar|conhecer|mostrar)',
            r'(quando|que horas|que dia|amanhã|hoje)'
        ]
        
        self.phone_pattern = r'\b\d{4,5}-?\d{4}\b'
        
        # Variações de bairros (São Paulo/Curitiba como exemplo)
        self.neighborhood_variations = {
            "água verde": ["Água Verde", "Ag. Verde", "região central"],
            "bigorrilho": ["Bigorrilho", "Big", "próximo ao centro"], 
            "batel": ["Batel", "região nobre", "area central"],
            "centro": ["Centro", "região central", "downtown"],
            "cabral": ["Cabral", "próximo ao centro"],
            "champagnat": ["Champagnat", "região valorizada"],
            "jardins": ["Jardins", "região dos Jardins", "área nobre"],
            "vila madalena": ["Vila Madalena", "V. Madalena", "região boêmia"]
        }
        
        # Variações de valores e metragem
        self.value_variations = [
            lambda v: f"R$ {v:,.2f}".replace(",", "."),
            lambda v: f"R$ {int(v/1000)}k",
            lambda v: f"cerca de R$ {v:,.0f}".replace(",", "."),
            lambda v: f"aproximadamente R$ {v:,.0f}".replace(",", ".")
        ]
        
    async def expand_from_firebase(self, limit: int = 100) -> List[TrainingExample]:
        """Captura conversas do Firebase e converte em exemplos"""
        examples = []
        
        try:
            from app.services.firebase_service import firebase_service
            
            # Buscar conversas dos últimos 30 dias
            cutoff = datetime.utcnow() - timedelta(days=30)
            
            # Query otimizada para conversas completas
            messages = await firebase_service.get_recent_conversations(
                since=cutoff, 
                limit=limit
            )
            
            # Agrupar por telefone para formar conversas
            conversations = self._group_messages_by_phone(messages)
            
            for phone, msgs in conversations.items():
                if len(msgs) < 2:  # Precisa de pelo menos user + assistant
                    continue
                
                example = self._convert_conversation_to_example(msgs, "firebase", phone)
                if example and self._is_valid_example(example):
                    examples.append(example)
                    logger.info(f"Exemplo capturado do Firebase: {phone}")
        
        except Exception as e:
            logger.error(f"Erro ao capturar do Firebase: {e}")
        
        return examples
    
    def load_whatsapp_export(self, csv_path: str) -> List[TrainingExample]:
        """Carrega export CSV do WhatsApp Business"""
        examples = []
        
        try:
            # Ler CSV com encoding correto
            df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
            
            # Agrupar por conversa (assumindo coluna 'phone' ou 'contact')
            phone_col = 'phone' if 'phone' in df.columns else 'contact'
            
            for phone, group in df.groupby(phone_col):
                messages = []
                
                for _, row in group.iterrows():
                    # Mapear colunas do export
                    role = "user" if row.get('direction') == 'incoming' else "assistant"
                    content = str(row.get('message', row.get('content', '')))
                    
                    if content and content != 'nan':
                        messages.append({
                            "role": role,
                            "content": content,
                            "timestamp": pd.to_datetime(row.get('timestamp'))
                        })
                
                if len(messages) >= 2:
                    example = self._convert_messages_to_example(
                        messages, "whatsapp_export", str(phone)
                    )
                    if example and self._is_valid_example(example):
                        examples.append(example)
            
            logger.info(f"Carregados {len(examples)} exemplos do WhatsApp export")
        
        except Exception as e:
            logger.error(f"Erro ao carregar WhatsApp export: {e}")
        
        return examples
    
    def _group_messages_by_phone(self, messages: List[Dict]) -> Dict[str, List[Dict]]:
        """Agrupa mensagens por telefone"""
        conversations = {}
        
        for msg in messages:
            phone = msg.get('user_phone', 'unknown')
            if phone not in conversations:
                conversations[phone] = []
            
            conversations[phone].append({
                "role": "user" if msg.get('direction') == 'received' else "assistant",
                "content": msg.get('message', ''),
                "timestamp": msg.get('timestamp')
            })
        
        # Ordenar mensagens por timestamp
        for phone in conversations:
            conversations[phone].sort(key=lambda x: x.get('timestamp', datetime.min))
        
        return conversations
    
    def _convert_conversation_to_example(self, 
                                       messages: List[Dict], 
                                       source: str, 
                                       conversation_id: str) -> Optional[TrainingExample]:
        """Converte conversa em exemplo de treinamento"""
        
        # Limpar e filtrar mensagens
        clean_messages = []
        for msg in messages:
            content = self._clean_message(msg.get('content', ''))
            if content and len(content) < 1500:  # Limite de caracteres
                clean_messages.append({
                    "role": msg.get('role'),
                    "content": content
                })
        
        if len(clean_messages) < 2:
            return None
        
        # Adicionar system message padrão
        system_msg = {
            "role": "system",
            "content": "Você é Sofia, assistente virtual especializada em imóveis da Allega Imóveis. Objetivo: ajudar o cliente e agendar visita quando apropriado."
        }
        
        final_messages = [system_msg] + clean_messages
        
        # Calcular lead score
        lead_score = self._calculate_lead_score(clean_messages)
        
        # Verificar se tem agendamento
        full_text = " ".join([m.get('content', '') for m in clean_messages])
        has_scheduling = self._has_scheduling_intent(full_text)
        
        # Gerar hash único
        conv_hash = self._generate_conversation_hash(final_messages)
        
        if conv_hash in self.seen_conversations:
            return None  # Duplicata
        
        self.seen_conversations.add(conv_hash)
        
        return TrainingExample(
            messages=final_messages,
            lead_score=lead_score,
            has_scheduling=has_scheduling,
            conversation_id=conversation_id,
            timestamp=datetime.utcnow(),
            source=source
        )
    
    def _convert_messages_to_example(self, 
                                   messages: List[Dict], 
                                   source: str, 
                                   conversation_id: str) -> Optional[TrainingExample]:
        """Converte lista de mensagens em exemplo"""
        return self._convert_conversation_to_example(messages, source, conversation_id)
    
    def _clean_message(self, content: str) -> str:
        """Limpa mensagem removendo informações sensíveis"""
        if not content:
            return ""
        
        # Anonimizar telefones
        content = re.sub(self.phone_pattern, '<TEL>', content)
        
        # Remover URLs longas
        content = re.sub(r'https?://[^\s]+', '<URL>', content)
        
        # Limpar caracteres especiais excessivos
        content = re.sub(r'[^\w\s\.\,\!\?\-\(\)\+\$\%\:\;]', '', content)
        
        # Normalizar espaços
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _calculate_lead_score(self, messages: List[Dict]) -> int:
        """Calcula score do lead (1-5) baseado no conteúdo"""
        full_text = " ".join([m.get('content', '') for m in messages]).lower()
        
        score = 1  # Base score
        
        # +1: Demonstrou interesse específico
        interest_keywords = ['quero', 'procuro', 'interesse', 'gostaria', 'preciso']
        if any(keyword in full_text for keyword in interest_keywords):
            score += 1
        
        # +1: Mencionou características específicas
        specifics = ['quartos', 'banheiros', 'vagas', 'metragem', 'm²', 'andar']
        if any(spec in full_text for spec in specifics):
            score += 1
        
        # +1: Perguntou sobre financiamento/valores
        financial = ['preço', 'valor', 'custo', 'financiamento', 'entrada', 'prestação']
        if any(fin in full_text for fin in financial):
            score += 1
        
        # +1: Pediu agendamento/visita
        scheduling = ['visita', 'agendar', 'ver', 'conhecer', 'quando', 'horário']
        if any(sched in full_text for sched in scheduling):
            score += 1
        
        return min(score, 5)  # Máximo 5
    
    def _has_scheduling_intent(self, text: str) -> bool:
        """Verifica se há intenção de agendamento"""
        text_lower = text.lower()
        
        for pattern in self.scheduling_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _generate_conversation_hash(self, messages: List[Dict]) -> str:
        """Gera hash único da conversa para evitar duplicatas"""
        content = "".join([m.get('content', '') for m in messages if m.get('role') != 'system'])
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _is_valid_example(self, example: TrainingExample) -> bool:
        """Valida se exemplo é adequado para treinamento"""
        
        # Precisa ter pelo menos system + user + assistant
        if len(example.messages) < 3:
            return False
        
        # Não pode ter mensagens vazias
        for msg in example.messages:
            if not msg.get('content', '').strip():
                return False
        
        # Assistant deve ter resposta de qualidade mínima
        assistant_msgs = [m for m in example.messages if m.get('role') == 'assistant']
        if not assistant_msgs:
            return False
        
        # Pelo menos uma resposta do assistant deve ter 10+ caracteres
        if not any(len(m.get('content', '')) >= 10 for m in assistant_msgs):
            return False
        
        return True
    
    async def data_augment_examples(self, 
                                   examples: List[TrainingExample], 
                                   target_multiplier: int = 3) -> List[TrainingExample]:
        """Aplica data augmentation nos exemplos"""
        augmented = []
        
        for example in examples:
            # Adicionar exemplo original
            augmented.append(example)
            
            # Gerar variações
            for i in range(target_multiplier - 1):
                try:
                    variation = await self._create_variation(example, i + 1)
                    if variation:
                        augmented.append(variation)
                except Exception as e:
                    logger.debug(f"Erro ao criar variação: {e}")
        
        logger.info(f"Dataset expandido: {len(examples)} → {len(augmented)} exemplos")
        return augmented
    
    async def _create_variation(self, example: TrainingExample, variation_id: int) -> Optional[TrainingExample]:
        """Cria uma variação do exemplo original"""
        
        new_messages = []
        
        for msg in example.messages:
            content = msg.get('content', '')
            
            if msg.get('role') == 'system':
                # System message permanece igual
                new_messages.append(msg.copy())
            
            elif msg.get('role') in ['user', 'assistant']:
                # Aplicar variações no conteúdo
                varied_content = self._apply_content_variations(content, variation_id)
                
                new_messages.append({
                    "role": msg.get('role'),
                    "content": varied_content
                })
        
        # Criar novo exemplo com ID único
        new_conv_id = f"{example.conversation_id}_var{variation_id}"
        
        return TrainingExample(
            messages=new_messages,
            lead_score=example.lead_score,
            has_scheduling=example.has_scheduling,
            conversation_id=new_conv_id,
            timestamp=example.timestamp,
            source=f"{example.source}_augmented"
        )
    
    def _apply_content_variations(self, content: str, variation_type: int) -> str:
        """Aplica diferentes tipos de variação no conteúdo"""
        
        if variation_type == 1:
            # Variação 1: Trocar bairros
            for original, variations in self.neighborhood_variations.items():
                if original.lower() in content.lower():
                    replacement = random.choice(variations)
                    content = re.sub(
                        re.escape(original), 
                        replacement, 
                        content, 
                        flags=re.IGNORECASE
                    )
        
        elif variation_type == 2:
            # Variação 2: Adicionar gírias/typos comuns
            substitutions = {
                "você": random.choice(["vc", "voce", "você"]),
                "não": random.choice(["nao", "ñ", "não"]),
                "está": random.choice(["tá", "esta", "está"]),
                "colega": random.choice(["colega", "kolega"]),
                "bom": random.choice(["bom", "bão"]),
                "também": random.choice(["também", "tbm", "tb"])
            }
            
            for original, replacement in substitutions.items():
                if random.random() < 0.3:  # 30% chance
                    content = re.sub(
                        r'\b' + re.escape(original) + r'\b',
                        replacement,
                        content,
                        flags=re.IGNORECASE
                    )
        
        elif variation_type == 3:
            # Variação 3: Alterar valores monetários
            value_pattern = r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
            
            def replace_value(match):
                value_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    value = float(value_str)
                    # Variar ±10%
                    variation = value * (0.9 + random.random() * 0.2)
                    formatter = random.choice(self.value_variations)
                    return formatter(variation)
                except:
                    return match.group(0)
            
            content = re.sub(value_pattern, replace_value, content)
        
        return content
    
    def save_expanded_dataset(self, 
                            examples: List[TrainingExample], 
                            filename: str = None) -> str:
        """Salva dataset expandido em formato JSONL"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sofia_expanded_{timestamp}.jsonl"
        
        output_path = self.output_dir / filename
        
        # Separar treino e validação (85%/15%)
        random.shuffle(examples)
        split_idx = int(len(examples) * 0.85)
        
        train_examples = examples[:split_idx]
        val_examples = examples[split_idx:]
        
        # Salvar dataset de treino
        train_path = output_path.with_suffix('.train.jsonl')
        self._save_jsonl(train_examples, train_path)
        
        # Salvar dataset de validação
        val_path = output_path.with_suffix('.val.jsonl')
        self._save_jsonl(val_examples, val_path)
        
        # Salvar estatísticas
        stats = self._generate_dataset_stats(examples)
        stats_path = output_path.with_suffix('.stats.json')
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Dataset salvo: {len(train_examples)} treino, {len(val_examples)} validação")
        logger.info(f"Arquivos: {train_path}, {val_path}, {stats_path}")
        
        return str(train_path)
    
    def _save_jsonl(self, examples: List[TrainingExample], path: Path):
        """Salva exemplos em formato JSONL"""
        with open(path, 'w', encoding='utf-8') as f:
            for example in examples:
                # Adicionar token <ASK> se tem agendamento
                messages = example.messages.copy()
                
                # Se última mensagem é assistant e tem agendamento, adicionar <ASK>
                if (messages and 
                    messages[-1].get('role') == 'assistant' and 
                    example.has_scheduling and 
                    example.lead_score >= 4):
                    
                    content = messages[-1]['content']
                    if not content.endswith('<ASK>'):
                        messages[-1]['content'] = content + ' <ASK>'
                
                # Adicionar metadata como comentário (opcional)
                json_line = {
                    "messages": messages,
                    # Metadados para análise posterior (comentar se necessário)
                    "_metadata": {
                        "lead_score": example.lead_score,
                        "has_scheduling": example.has_scheduling,
                        "source": example.source,
                        "conversation_id": example.conversation_id
                    }
                }
                
                f.write(json.dumps(json_line, ensure_ascii=False) + '\\n')
    
    def _generate_dataset_stats(self, examples: List[TrainingExample]) -> Dict[str, Any]:
        """Gera estatísticas do dataset"""
        
        total = len(examples)
        by_score = {}
        by_source = {}
        with_scheduling = 0
        
        for example in examples:
            # Por score
            score = example.lead_score
            by_score[score] = by_score.get(score, 0) + 1
            
            # Por fonte
            source = example.source
            by_source[source] = by_source.get(source, 0) + 1
            
            # Com agendamento
            if example.has_scheduling:
                with_scheduling += 1
        
        return {
            "total_examples": total,
            "by_lead_score": by_score,
            "by_source": by_source,
            "with_scheduling": with_scheduling,
            "scheduling_rate": with_scheduling / total if total > 0 else 0,
            "generated_at": datetime.utcnow().isoformat(),
            "recommended_split": {
                "train": int(total * 0.85),
                "validation": int(total * 0.15)
            }
        }

# Instância global
dataset_expander = DatasetExpander()