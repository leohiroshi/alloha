"""
State Machine para Conversas - Evita Race Conditions e Permite Paralelização
Suporta volume de 10x sem reescrever código core
"""
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """Estados da conversa para gerenciar leads de forma escalável"""
    PENDING = "pending"          # Mensagem recebida, aguardando processamento
    QUALIFIED = "qualified"      # Lead qualificado, interesse confirmado
    NURTURE = "nurture"         # Lead em processo de nutrição
    CLOSED = "closed"           # Lead convertido ou perdido
    ERROR = "error"             # Estado de erro para retry

class ConversationManager:
    """Gerenciador de estado de conversas thread-safe"""
    
    def __init__(self):
        self._conversations: Dict[str, Dict] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
    async def get_or_create_conversation(self, user_phone: str) -> Dict[str, Any]:
        """Thread-safe: pega ou cria conversa"""
        if user_phone not in self._locks:
            self._locks[user_phone] = asyncio.Lock()
            
        async with self._locks[user_phone]:
            if user_phone not in self._conversations:
                self._conversations[user_phone] = {
                    "user_phone": user_phone,
                    "state": ConversationState.PENDING,
                    "created_at": datetime.utcnow(),
                    "last_message": None,
                    "lead_score": 0,
                    "next_action": "process_initial_message",
                    "slot": None,
                    "metadata": {}
                }
                logger.info(f"Nova conversa criada: {user_phone}")
            
            return self._conversations[user_phone]
    
    async def transition_state(self, user_phone: str, new_state: ConversationState, 
                              metadata: Dict[str, Any] = None) -> bool:
        """Thread-safe: transição de estado"""
        if user_phone not in self._locks:
            return False
            
        async with self._locks[user_phone]:
            if user_phone in self._conversations:
                old_state = self._conversations[user_phone]["state"]
                self._conversations[user_phone]["state"] = new_state
                self._conversations[user_phone]["updated_at"] = datetime.utcnow()
                
                if metadata:
                    self._conversations[user_phone]["metadata"].update(metadata)
                
                logger.info(f"State transition: {user_phone} {old_state.value} → {new_state.value}")
                return True
        return False
    
    async def update_lead_score(self, user_phone: str, score: int, next_action: str, slot: datetime = None):
        """Atualiza score do lead de forma thread-safe"""
        if user_phone not in self._locks:
            return False
            
        async with self._locks[user_phone]:
            if user_phone in self._conversations:
                conv = self._conversations[user_phone]
                conv["lead_score"] = score
                conv["next_action"] = next_action
                conv["slot"] = slot
                conv["updated_at"] = datetime.utcnow()
                
                # Auto-transition baseado no score
                if score >= 70:
                    await self.transition_state(user_phone, ConversationState.QUALIFIED)
                elif score >= 40:
                    await self.transition_state(user_phone, ConversationState.NURTURE)
                
                return True
        return False
    
    def get_conversation_state(self, user_phone: str) -> Optional[ConversationState]:
        """Leitura rápida do estado (sem lock para performance)"""
        return self._conversations.get(user_phone, {}).get("state")
    
    def get_active_conversations(self) -> Dict[str, Dict]:
        """Retorna conversas ativas para monitoramento"""
        return {
            phone: conv for phone, conv in self._conversations.items()
            if conv["state"] in [ConversationState.PENDING, ConversationState.QUALIFIED, ConversationState.NURTURE]
        }

# Instância global thread-safe
conversation_manager = ConversationManager()