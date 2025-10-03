"""
Sistema de Score de Urgência - Diferencial 1
Detecta sinais de urgência e alerta corretores em < 5min
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re

from app.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)

@dataclass
class UrgencyAlert:
    """Alert de urgência para corretor"""
    phone: str
    message: str
    urgency_score: int  # 1-5
    urgency_reasons: List[str]
    detected_at: datetime
    client_profile: Dict[str, Any]
    suggested_actions: List[str]
    
class UrgencyScoreSystem:
    """Sistema de detecção de urgência em tempo real"""
    
    def __init__(self):
        # Padrões de urgência com pesos
        self.urgency_patterns = {
            # CRÍTICO (Score 5): Situações de emergência
            5: [
                r'(despej\w+|despejo|sendo despejado)',
                r'(preciso sair|tenho que sair).{0,20}(hoje|amanhã|sexta|fim.?de.?semana)',
                r'(emergência|emergencial|situação crítica)',
                r'(sem lugar|não tenho onde|homeless)',
                r'(separação|divórcio).{0,30}(urgente|rápido|já)',
            ],
            
            # ALTO (Score 4): Situações com prazo definido
            4: [
                r'(até|antes d[eo]).{0,10}(sexta|sábado|domingo|próxima semana)',
                r'(casamento|trabalho novo|transferência).{0,20}(próxim\w+|dias|semana)',
                r'(contrato vence|aluguel acaba|termina).{0,15}(\d{1,2}\/\d{1,2}|dias|semana)',
                r'(mudança marcada|van contratada|caminhão)',
                r'(filho nasce|bebê|nascimento).{0,20}(dias|semana|mês)',
            ],
            
            # MÉDIO (Score 3): Procura ativa com motivação
            3: [
                r'(procurando há|à procura há).{0,10}(semanas|meses)',
                r'(visitei \d+|vi vários|já visitei)',
                r'(corretor anterior|outra imobiliária).{0,20}(não resolve|demorou|lento)',
                r'(orçamento aprovado|financiamento ok|entrada pronta)',
                r'(quero ver|posso visitar).{0,15}(hoje|amanhã|essa semana)',
            ],
            
            # BAIXO (Score 2): Interesse com limitações
            2: [
                r'(só olhando|apenas curiosidade)',
                r'(talvez|pode ser que|não tenho certeza)',
                r'(mês que vem|ano que vem|futuro)',
                r'(vou pensar|preciso conversar)',
            ]
        }
        
        # Palavras que indicam motivação específica
        self.motivation_keywords = {
            'family': ['filho', 'bebê', 'família', 'casamento', 'casal'],
            'work': ['trabalho', 'emprego', 'transferência', 'promoção'],
            'financial': ['financiamento', 'aprovado', 'entrada', 'orçamento'],
            'lifestyle': ['espaço', 'qualidade de vida', 'segurança', 'localização'],
            'investment': ['investimento', 'renda', 'valorização', 'negócio']
        }
        
        # Actions recomendadas por score
        self.suggested_actions = {
            5: [
                "LIGAR IMEDIATAMENTE - Situação crítica",
                "Agendar visita para HOJE se possível", 
                "Preparar documentação para assinatura rápida",
                "Verificar imóveis disponíveis para entrega imediata"
            ],
            4: [
                "Contatar em até 30 minutos",
                "Agendar visita para amanhã ou próximos dias",
                "Preparar 3-5 opções pré-selecionadas",
                "Questionar prazo específico da necessidade"
            ],
            3: [
                "Responder em até 2 horas",
                "Agendar visita na próxima semana",
                "Enviar portfólio personalizado",
                "Fazer follow-up em 48h"
            ],
            2: [
                "Responder em até 24 horas",
                "Adicionar à nurturing list",
                "Enviar conteúdo educativo",
                "Follow-up semanal"
            ]
        }
    
    async def analyze_urgency(self, 
                            message: str, 
                            phone: str,
                            conversation_history: List[Dict] = None) -> UrgencyAlert:
        """Analisa urgência e gera alert para corretor"""
        
        try:
            # Calcular score base
            urgency_score, reasons = self._calculate_urgency_score(message)
            
            # Ajustar com histórico
            if conversation_history:
                historical_score = self._analyze_conversation_history(conversation_history)
                urgency_score = max(urgency_score, historical_score)
            
            # Perfil do cliente
            client_profile = await self._build_client_profile(phone, conversation_history)
            
            # Actions sugeridas
            suggested_actions = self.suggested_actions.get(urgency_score, self.suggested_actions[2])
            
            alert = UrgencyAlert(
                phone=phone,
                message=message,
                urgency_score=urgency_score,
                urgency_reasons=reasons,
                detected_at=datetime.utcnow(),
                client_profile=client_profile,
                suggested_actions=suggested_actions
            )
            
            # Salvar alert se urgência >= 3
            if urgency_score >= 3:
                await self._save_urgency_alert(alert)
                
                # Notificar corretor se urgência >= 4
                if urgency_score >= 4:
                    await self._notify_broker_urgent(alert)
            
            logger.info(f"Urgência analisada: {phone} = {urgency_score}/5 ({len(reasons)} razões)")
            return alert
            
        except Exception as e:
            logger.error(f"Erro na análise de urgência: {e}")
            
            # Alert mínimo
            return UrgencyAlert(
                phone=phone,
                message=message,
                urgency_score=1,
                urgency_reasons=[],
                detected_at=datetime.utcnow(),
                client_profile={},
                suggested_actions=self.suggested_actions[2]
            )
    
    def _calculate_urgency_score(self, message: str) -> tuple[int, List[str]]:
        """Calcula score de urgência baseado em padrões"""
        
        message_lower = message.lower()
        max_score = 1
        reasons = []
        
        # Verificar padrões por nível de urgência
        for score, patterns in self.urgency_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, message_lower, re.IGNORECASE)
                if matches:
                    max_score = max(max_score, score)
                    reason = f"Padrão urgência {score}: '{matches[0]}'"
                    reasons.append(reason)
        
        # Boost por múltiplas menções de tempo
        time_references = len(re.findall(
            r'(hoje|amanhã|sexta|semana|dias|urgente|rápido|já|preciso)',
            message_lower
        ))
        if time_references >= 3:
            max_score = min(max_score + 1, 5)
            reasons.append(f"Múltiplas referências de tempo ({time_references})")
        
        # Boost por motivação específica
        for category, keywords in self.motivation_keywords.items():
            if any(kw in message_lower for kw in keywords):
                max_score = min(max_score + 1, 5)
                reasons.append(f"Motivação {category} detectada")
                break
        
        return max_score, reasons
    
    def _analyze_conversation_history(self, history: List[Dict]) -> int:
        """Analisa histórico para detectar urgência crescente"""
        
        if not history or len(history) < 3:
            return 1
        
        # Verificar mensagens recentes por urgência
        recent_messages = history[-5:]  # Últimas 5 mensagens
        urgency_scores = []
        
        for msg in recent_messages:
            content = msg.get('content', '')
            if content:
                score, _ = self._calculate_urgency_score(content)
                urgency_scores.append(score)
        
        # Se urgência está crescendo
        if len(urgency_scores) >= 3:
            if urgency_scores[-1] > urgency_scores[-3]:
                return min(max(urgency_scores) + 1, 5)
        
        return max(urgency_scores) if urgency_scores else 1
    
    async def _build_client_profile(self, phone: str, history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Constrói perfil do cliente usando dados do Supabase (conversations + messages)."""

        profile = {
            'phone': phone,
            'first_contact': datetime.utcnow().isoformat(),
            'total_messages': 0,
            'engagement_level': 'low',
            'preferences': {},
            'urgency_history': []
        }
        try:
            # Buscar conversa mais recente
            conversation_result = await asyncio.to_thread(
                lambda: supabase_client.client.table('conversations')
                    .select('id, created_at, last_message_at')
                    .eq('phone_number', phone)
                    .order('created_at')
                    .limit(1)
                    .execute()
            )
            conversation = conversation_result.data[0] if conversation_result.data else None

            if not conversation:
                return profile

            profile['first_contact'] = conversation.get('created_at', profile['first_contact'])

            # Buscar mensagens da conversa
            messages_result = await asyncio.to_thread(
                lambda: supabase_client.client.table('messages')
                    .select('content, created_at, direction')
                    .eq('conversation_id', conversation['id'])
                    .order('created_at')
                    .limit(200)
                    .execute()
            )
            messages = messages_result.data or []
            profile['total_messages'] = len(messages)

            # Engajamento
            if profile['total_messages'] > 10:
                profile['engagement_level'] = 'high'
            elif profile['total_messages'] > 5:
                profile['engagement_level'] = 'medium'

            # Preferências
            all_text = ' '.join([m.get('content', '') for m in messages if m.get('content')])
            if all_text:
                profile['preferences'] = self._extract_preferences(all_text)

            return profile
        except Exception as e:
            logger.debug(f"Erro ao construir perfil (Supabase): {e}")
            return profile
    
    def _extract_preferences(self, text: str) -> Dict[str, Any]:
        """Extrai preferências do texto consolidado"""
        
        text_lower = text.lower()
        preferences = {}
        
        # Bairros mencionados
        neighborhoods = ["água verde", "bigorrilho", "batel", "centro", "cabral", "jardins"]
        mentioned_neighborhoods = [n for n in neighborhoods if n in text_lower]
        if mentioned_neighborhoods:
            preferences["neighborhoods"] = mentioned_neighborhoods
        
        # Orçamento
        price_matches = re.findall(r'(\d+\.?\d*)\s*mil', text_lower)
        if price_matches:
            preferences["budget_range"] = [float(p) * 1000 for p in price_matches[-2:]]
        
        # Quartos
        bedroom_matches = re.findall(r'(\d+)\s*quarto', text_lower)
        if bedroom_matches:
            preferences["bedrooms"] = int(bedroom_matches[-1])
        
        # Tipo de imóvel
        if "apartamento" in text_lower or "apto" in text_lower:
            preferences["property_type"] = "apartamento"
        elif "casa" in text_lower:
            preferences["property_type"] = "casa"
        
        return preferences
    
    async def _save_urgency_alert(self, alert: UrgencyAlert):
        """Salva alerta de urgência no Supabase (urgency_alerts)."""
        try:
            alert_data = {
                'phone': alert.phone,
                'message': alert.message[:500],
                'urgency_score': alert.urgency_score,
                'urgency_reasons': alert.urgency_reasons,
                'detected_at': alert.detected_at.isoformat(),
                'client_profile': alert.client_profile,
                'suggested_actions': alert.suggested_actions,
                'status': 'pending',
                'assigned_broker': None,
                'created_at': datetime.utcnow().isoformat()
            }
            await asyncio.to_thread(
                lambda: supabase_client.client.table('urgency_alerts')
                    .insert(alert_data)
                    .execute()
            )
            logger.info(f"Alert urgência salvo (Supabase): {alert.phone} (score {alert.urgency_score})")
        except Exception as e:
            logger.error(f"Erro ao salvar alert de urgência (Supabase): {e}")
    
    async def _notify_broker_urgent(self, alert: UrgencyAlert):
        """Notifica corretor sobre urgência alta (Supabase)."""
        try:
            notification_data = {
                'type': 'urgent_lead',
                'phone': alert.phone,
                'urgency_score': alert.urgency_score,
                'message_preview': alert.message[:100],
                'suggested_actions': alert.suggested_actions[:2],
                'detected_at': alert.detected_at.isoformat(),
                'client_profile': {
                    'engagement': alert.client_profile.get('engagement_level', 'unknown'),
                    'total_messages': alert.client_profile.get('total_messages', 0)
                },
                'status': 'sent',
                'created_at': datetime.utcnow().isoformat()
            }
            await asyncio.to_thread(
                lambda: supabase_client.client.table('broker_notifications')
                    .insert(notification_data)
                    .execute()
            )
            logger.warning(f"🚨 URGENT LEAD (Supabase): {alert.phone} (score {alert.urgency_score})")
        except Exception as e:
            logger.error(f"Erro ao notificar corretor (Supabase): {e}")
    
    async def get_pending_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera alerts pendentes (Supabase) últimos 7 dias."""
        try:
            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            result = await asyncio.to_thread(
                lambda: supabase_client.client.table('urgency_alerts')
                    .select('*')
                    .gte('detected_at', seven_days_ago)
                    .eq('status', 'pending')
                    .order('urgency_score', desc=True)
                    .order('detected_at', desc=True)
                    .limit(limit)
                    .execute()
            )
            alerts = result.data or []
            logger.info(f"Recuperados {len(alerts)} alerts pendentes (Supabase)")
            return alerts
        except Exception as e:
            logger.error(f"Erro ao recuperar alerts pendentes (Supabase): {e}")
            return []
    
    async def mark_alert_as_contacted(self, alert_id: str, broker_name: str):
        """Marca alert como contatado (Supabase)."""
        try:
            await asyncio.to_thread(
                lambda: supabase_client.client.table('urgency_alerts')
                    .update({
                        'status': 'contacted',
                        'contacted_at': datetime.utcnow().isoformat(),
                        'contacted_by': broker_name
                    })
                    .eq('id', alert_id)
                    .execute()
            )
            logger.info(f"Alert {alert_id} marcado como contatado por {broker_name} (Supabase)")
        except Exception as e:
            logger.error(f"Erro ao marcar alert como contatado (Supabase): {e}")
    
    def get_urgency_stats(self) -> Dict[str, Any]:
        """Estatísticas do sistema de urgência"""
        
        return {
            "urgency_patterns_count": sum(len(patterns) for patterns in self.urgency_patterns.values()),
            "motivation_categories": len(self.motivation_keywords),
            "action_levels": len(self.suggested_actions)
        }

# Instância global
urgency_score_system = UrgencyScoreSystem()