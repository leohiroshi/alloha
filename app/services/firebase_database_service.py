import logging
from typing import Optional, Dict, List
from .firebase_service import firebase_service

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.firebase = firebase_service
    
    async def check_connection(self) -> bool:
        """Verificar conexão com o banco"""
        return self.firebase.is_connected()
    
    async def save_message(self, user_phone: str, message: str, direction: str, metadata: Dict = None) -> bool:
        """Salvar mensagem no banco"""
        try:
            success = await self.firebase.save_message(user_phone, message, direction, metadata)
            if success:
                logger.info(f"💾 Mensagem salva: {user_phone} - {direction}")
            return success
        except Exception as e:
            logger.error(f"❌ Erro ao salvar mensagem: {str(e)}")
            return False
    
    async def get_conversation_history(self, user_phone: str, limit: int = 10) -> List[Dict]:
        """Obter histórico de conversa"""
        try:
            return await self.firebase.get_conversation_history(user_phone, limit)
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {str(e)}")
            return []
    
    async def save_user_profile(self, user_phone: str, profile_data: Dict) -> bool:
        """Salvar perfil do usuário"""
        try:
            return await self.firebase.save_user_profile(user_phone, profile_data)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar perfil: {str(e)}")
            return False
    
    async def get_user_profile(self, user_phone: str) -> Optional[Dict]:
        """Obter perfil do usuário"""
        try:
            return await self.firebase.get_user_profile(user_phone)
        except Exception as e:
            logger.error(f"❌ Erro ao obter perfil: {str(e)}")
            return None
    
    async def save_analytics(self, event_type: str, data: Dict) -> bool:
        """Salvar dados de analytics"""
        try:
            return await self.firebase.save_analytics(event_type, data)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar analytics: {str(e)}")
            return False
    
    async def get_user_stats(self, user_phone: str) -> Dict:
        """Obter estatísticas do usuário"""
        try:
            return await self.firebase.get_user_stats(user_phone)
        except Exception as e:
            logger.error(f"❌ Erro ao obter stats: {str(e)}")
            return {"total_messages": 0, "first_contact": None, "last_contact": None}
