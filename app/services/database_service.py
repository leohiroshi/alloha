import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configurar o tipo de banco
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "firebase")

class DatabaseService:
    def __init__(self):
        if DATABASE_TYPE == "firebase":
            from app.services.firebase_service import FirebaseService
            self.firebase_service = FirebaseService()
            self._use_firebase = True
        else:
            # PostgreSQL como backup
            self.connection_string = os.getenv("DATABASE_URL", "")
            self.pool = None
            self._use_firebase = False
            
    async def check_connection(self) -> bool:
        """Verificar se a conexão com o banco está ativa"""
        try:
            if self._use_firebase:
                return self.firebase_service.check_connection()
            else:
                # PostgreSQL connection check
                if not self.pool:
                    await self.init_pool()
                
                import asyncpg
                async with self.pool.acquire() as connection:
                    await connection.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False
    
    async def save_message(self, user_phone: str, message_text: str, message_type: str = "received") -> bool:
        """Salvar mensagem no banco de dados"""
        try:
            if self._use_firebase:
                return await self.firebase_service.save_message(user_phone, message_text, message_type)
            else:
                # PostgreSQL implementation
                if not self.pool:
                    await self.init_pool()
                
                import asyncpg
                async with self.pool.acquire() as connection:
                    await connection.execute(
                        "INSERT INTO messages (user_phone, message_text, message_type) VALUES ($1, $2, $3)",
                        user_phone, message_text, message_type
                    )
                return True
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return False
    
    async def get_conversation_history(self, user_phone: str, limit: int = 10) -> List[Dict]:
        """Obter histórico de conversas de um usuário"""
        try:
            if self._use_firebase:
                return await self.firebase_service.get_conversation_history(user_phone, limit)
            else:
                # PostgreSQL implementation
                if not self.pool:
                    await self.init_pool()
                
                import asyncpg
                async with self.pool.acquire() as connection:
                    rows = await connection.fetch(
                        "SELECT message_text, message_type, timestamp FROM messages WHERE user_phone = $1 ORDER BY timestamp DESC LIMIT $2",
                        user_phone, limit
                    )
                    
                    return [
                        {
                            "message": row["message_text"],
                            "type": row["message_type"],
                            "timestamp": row["timestamp"].isoformat()
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    async def save_user_profile(self, user_phone: str, profile_data: Dict[str, Any]) -> bool:
        """Salvar dados do perfil do usuário"""
        try:
            if self._use_firebase:
                return await self.firebase_service.save_user_profile(user_phone, profile_data)
            else:
                # PostgreSQL implementation
                if not self.pool:
                    await self.init_pool()
                
                import asyncpg, json
                async with self.pool.acquire() as connection:
                    await connection.execute(
                        """
                        INSERT INTO users (phone_number, name, email, preferences, updated_at) 
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                        ON CONFLICT (phone_number) 
                        DO UPDATE SET 
                            name = EXCLUDED.name,
                            email = EXCLUDED.email,
                            preferences = EXCLUDED.preferences,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        user_phone,
                        profile_data.get("name"),
                        profile_data.get("email"),
                        json.dumps(profile_data.get("preferences", {}))
                    )
                return True
        except Exception as e:
            logger.error(f"Error saving user profile: {str(e)}")
            return False
    
    async def get_user_profile(self, user_phone: str) -> Optional[Dict[str, Any]]:
        """Obter perfil do usuário"""
        try:
            if self._use_firebase:
                return await self.firebase_service.get_user_profile(user_phone)
            else:
                # PostgreSQL implementation
                if not self.pool:
                    await self.init_pool()
                
                import asyncpg
                async with self.pool.acquire() as connection:
                    row = await connection.fetchrow(
                        "SELECT name, email, preferences, created_at, updated_at FROM users WHERE phone_number = $1",
                        user_phone
                    )
                    
                    if row:
                        return {
                            "name": row["name"],
                            "email": row["email"],
                            "preferences": row["preferences"] or {},
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                        }
                    return None
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def save_analytics_event(self, event_type: str, user_phone: str, data: Dict[str, Any]) -> bool:
        """Salvar evento de analytics"""
        try:
            if self._use_firebase:
                return await self.firebase_service.save_analytics_event(event_type, user_phone, data)
            else:
                # PostgreSQL implementation
                if not self.pool:
                    await self.init_pool()
                
                import asyncpg, json
                async with self.pool.acquire() as connection:
                    await connection.execute(
                        "INSERT INTO analytics (event_type, user_phone, event_data) VALUES ($1, $2, $3)",
                        event_type, user_phone, json.dumps(data)
                    )
                return True
        except Exception as e:
            logger.error(f"Error saving analytics event: {str(e)}")
            return False

    # PostgreSQL methods (só usado se não for Firebase)
    async def init_pool(self):
        """Inicializar pool de conexões PostgreSQL"""
        if not self.pool and not self._use_firebase:
            try:
                import asyncpg
                self.pool = await asyncpg.create_pool(self.connection_string)
                await self.create_tables()
                logger.info("Database pool initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {str(e)}")
                raise
    
    async def create_tables(self):
        """Criar tabelas PostgreSQL necessárias"""
        create_messages_table = """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_phone VARCHAR(20) NOT NULL,
            message_text TEXT NOT NULL,
            message_type VARCHAR(20) NOT NULL DEFAULT 'received',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}'
        )
        """
        
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            phone_number VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100),
            email VARCHAR(100),
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_analytics_table = """
        CREATE TABLE IF NOT EXISTS analytics (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            user_phone VARCHAR(20),
            event_data JSONB DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        import asyncpg
        async with self.pool.acquire() as connection:
            await connection.execute(create_messages_table)
            await connection.execute(create_users_table)
            await connection.execute(create_analytics_table)
