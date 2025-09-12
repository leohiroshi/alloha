import firebase_admin
from firebase_admin import credentials, firestore
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List
import base64

logger = logging.getLogger(__name__)

class FirebaseService:
    def __init__(self):
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Inicializar Firebase"""
        try:
            # Verificar se já foi inicializado
            if firebase_admin._apps:
                self.db = firestore.client()
                return
            
            # Tentar carregar credenciais do ambiente
            firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
            
            if firebase_credentials:
                # Se credenciais estão em base64 (para GitHub Actions)
                try:
                    if firebase_credentials.startswith('eyJ'):  # JSON base64
                        decoded_creds = base64.b64decode(firebase_credentials).decode('utf-8')
                        cred_dict = json.loads(decoded_creds)
                    else:
                        cred_dict = json.loads(firebase_credentials)
                    
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    logger.info("✅ Firebase inicializado com credenciais do ambiente")
                except Exception as e:
                    logger.error(f"❌ Erro ao carregar credenciais: {str(e)}")
                    self.db = None
            else:
                # Tentar carregar arquivo local para desenvolvimento
                cred_file = "firebase-credentials.json"
                if os.path.exists(cred_file):
                    cred = credentials.Certificate(cred_file)
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    logger.info("✅ Firebase inicializado com arquivo local")
                else:
                    logger.warning("⚠️ Firebase não configurado - usando modo offline")
                    self.db = None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Firebase: {str(e)}")
            self.db = None
    
    def is_connected(self) -> bool:
        """Verificar se Firebase está conectado"""
        return self.db is not None
    
    def check_connection(self) -> bool:
        """Verificar conexão com Firebase"""
        return self.is_connected()
    
    async def save_message(self, user_phone: str, message: str, direction: str, metadata: Dict = None) -> bool:
        """Salvar mensagem no Firestore"""
        try:
            if not self.db:
                logger.warning("Firebase não conectado - mensagem não salva")
                return False
            
            message_data = {
                "user_phone": user_phone,
                "message": message,
                "direction": direction,  # "received" ou "sent"
                "timestamp": datetime.now(),
                "metadata": metadata or {}
            }
            
            # Salvar na coleção de mensagens
            doc_ref = self.db.collection("messages").document()
            doc_ref.set(message_data)
            
            # Atualizar última conversa do usuário
            conversation_ref = self.db.collection("conversations").document(user_phone)
            conversation_ref.set({
                "last_message": message,
                "last_message_direction": direction,
                "last_updated": datetime.now(),
                "total_messages": firestore.Increment(1)
            }, merge=True)
            
            logger.info(f"Mensagem salva: {user_phone} - {direction}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar mensagem: {str(e)}")
            return False
    
    async def get_conversation_history(self, user_phone: str, limit: int = 10) -> List[Dict]:
        """Obter histórico de conversa"""
        try:
            if not self.db:
                return []
            
            messages_ref = self.db.collection("messages")
            query = (messages_ref
                    .where("user_phone", "==", user_phone)
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)
                    .limit(limit))
            
            docs = query.stream()
            messages = []
            
            for doc in docs:
                message_data = doc.to_dict()
                message_data["id"] = doc.id
                messages.append(message_data)
            
            # Retornar em ordem cronológica
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {str(e)}")
            return []
    
    async def save_user_profile(self, user_phone: str, profile_data: Dict) -> bool:
        """Salvar perfil do usuário"""
        try:
            if not self.db:
                return False
            
            profile_data["last_updated"] = datetime.now()
            profile_data["phone"] = user_phone
            
            user_ref = self.db.collection("users").document(user_phone)
            user_ref.set(profile_data, merge=True)
            
            logger.info(f"👤 Perfil salvo: {user_phone}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar perfil: {str(e)}")
            return False
    
    async def get_user_profile(self, user_phone: str) -> Optional[Dict]:
        """Obter perfil do usuário"""
        try:
            if not self.db:
                return None
            
            user_ref = self.db.collection("users").document(user_phone)
            doc = user_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter perfil: {str(e)}")
            return None
    
    async def save_analytics(self, event_type: str, data: Dict) -> bool:
        """Salvar dados de analytics"""
        try:
            if not self.db:
                return False
            
            analytics_data = {
                "event_type": event_type,
                "timestamp": datetime.now(),
                "data": data
            }
            
            doc_ref = self.db.collection("analytics").document()
            doc_ref.set(analytics_data)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar analytics: {str(e)}")
            return False
    
    async def get_user_stats(self, user_phone: str) -> Dict:
        """Obter estatísticas do usuário"""
        try:
            if not self.db:
                return {"total_messages": 0, "first_contact": None, "last_contact": None}
            
            # Contar mensagens totais
            messages_ref = self.db.collection("messages")
            query = messages_ref.where("user_phone", "==", user_phone)
            docs = list(query.stream())
            
            if not docs:
                return {"total_messages": 0, "first_contact": None, "last_contact": None}
            
            # Calcular estatísticas
            timestamps = [doc.to_dict()["timestamp"] for doc in docs]
            
            return {
                "total_messages": len(docs),
                "first_contact": min(timestamps),
                "last_contact": max(timestamps),
                "messages_today": len([t for t in timestamps if t.date() == datetime.now().date()])
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter stats: {str(e)}")
            return {"total_messages": 0, "first_contact": None, "last_contact": None}
    
    async def save_property_data(self, property_data: dict) -> bool:
        """Salva dados de imóveis no Firebase"""
        try:
            if not self.db:
                return False
                
            # Salvar dados principais de imóveis
            properties_ref = self.db.collection('properties')
            doc_ref = properties_ref.document('allega_data')
            
            data_to_save = {
                'data': property_data,
                'last_updated': datetime.now(),
                'source': 'allega_scraper'
            }
            
            doc_ref.set(data_to_save)
            logger.info("📊 Dados de imóveis salvos no Firebase")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar dados de imóveis: {str(e)}")
            return False
    
    async def get_property_data(self) -> dict:
        """Obtém dados de imóveis do Firebase"""
        try:
            if not self.db:
                return {}
                
            doc_ref = self.db.collection('properties').document('allega_data')
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return data.get('data', {})
            else:
                return {}
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter dados de imóveis: {str(e)}")
            return {}
    
    async def save_property_search(self, user_id: str, criteria: dict, results_count: int) -> bool:
        """Salva busca de imóveis para analytics"""
        try:
            if not self.db:
                return False
                
            search_data = {
                'user_id': user_id,
                'criteria': criteria,
                'results_count': results_count,
                'timestamp': datetime.now(),
                'type': 'property_search'
            }
            
            # Salvar na coleção de buscas
            self.db.collection('property_searches').add(search_data)
            
            # Atualizar contador do usuário se existir
            try:
                user_ref = self.db.collection('users').document(user_id)
                user_doc = user_ref.get()
                if user_doc.exists:
                    current_data = user_doc.to_dict()
                    analytics = current_data.get('analytics', {})
                    analytics['property_searches'] = analytics.get('property_searches', 0) + 1
                    analytics['last_property_search'] = datetime.now()
                    
                    user_ref.update({'analytics': analytics})
            except Exception:
                pass  # Ignore if user doesn't exist
            
            logger.info(f"🔍 Busca de imóveis salva para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar busca de imóveis: {str(e)}")
            return False
    
    async def clear_user_conversation(self, user_phone: str) -> bool:
        """Limpa todas as mensagens de um usuário específico"""
        try:
            if not self.db:
                logger.error("❌ Firebase não inicializado")
                return False
            
            # Buscar e deletar todas as mensagens do usuário
            messages_ref = self.db.collection('messages').where('user_phone', '==', user_phone)
            docs = messages_ref.stream()
            
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1
            
            logger.info(f"✅ {deleted_count} mensagens removidas para {user_phone}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar conversa do usuário: {str(e)}")
            return False
    
    async def clear_all_conversations(self) -> bool:
        """Limpa TODAS as conversas do Firebase"""
        try:
            if not self.db:
                logger.error("❌ Firebase não inicializado")
                return False
            
            # Deletar todas as mensagens
            messages_ref = self.db.collection('messages')
            docs = messages_ref.stream()
            
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1
            
            logger.info(f"🔥 TODAS as conversas removidas! Total: {deleted_count} mensagens")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar todas as conversas: {str(e)}")
            return False
    
    def list_all_users(self) -> List[str]:
        """Lista todos os usuários que já conversaram"""
        try:
            if not self.db:
                logger.error("❌ Firebase não inicializado")
                return []
            
            messages_ref = self.db.collection('messages')
            docs = messages_ref.stream()
            
            users = set()
            for doc in docs:
                data = doc.to_dict()
                if 'user_phone' in data:
                    users.add(data['user_phone'])
            
            return list(users)
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar usuários: {str(e)}")
            return []

# Instância global
firebase_service = FirebaseService()
