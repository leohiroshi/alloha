import asyncpg
import logging
import os
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "")
        self.pool = None
    
    async def init_pool(self):
        """Inicializar pool de conexões"""
        try:
            if self.database_url:
                self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=10)
                await self.create_tables()
                logger.info("Database pool initialized successfully")
            else:
                logger.warning("Database URL not configured")
        except Exception as e:
            logger.error(f"Error initializing database pool: {str(e)}")
    
    async def create_tables(self):
        """Criar tabelas necessárias"""
        try:
            if not self.pool:
                return
            
            async with self.pool.acquire() as conn:
                # Tabela de usuários
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(20) UNIQUE NOT NULL,
                        name VARCHAR(100),
                        email VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabela de mensagens
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(20) NOT NULL,
                        message_text TEXT NOT NULL,
                        message_type VARCHAR(20) NOT NULL, -- 'received' or 'sent'
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (phone_number) REFERENCES users(phone_number) ON DELETE CASCADE
                    )
                """)
                
                # Tabela de conversas/sessões
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(20) NOT NULL,
                        context TEXT,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'active',
                        FOREIGN KEY (phone_number) REFERENCES users(phone_number) ON DELETE CASCADE
                    )
                """)
                
                logger.info("Database tables created/verified successfully")
                
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
    
    async def save_message(self, phone_number: str, message_text: str, message_type: str):
        """Salvar mensagem no banco"""
        try:
            if not self.pool:
                logger.warning("Database not available")
                return
            
            async with self.pool.acquire() as conn:
                # Primeiro, garantir que o usuário existe
                await conn.execute("""
                    INSERT INTO users (phone_number) 
                    VALUES ($1) 
                    ON CONFLICT (phone_number) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
                """, phone_number)
                
                # Salvar mensagem
                await conn.execute("""
                    INSERT INTO messages (phone_number, message_text, message_type)
                    VALUES ($1, $2, $3)
                """, phone_number, message_text, message_type)
                
                logger.info(f"Message saved: {phone_number} - {message_type}")
                
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
    
    async def get_user_context(self, phone_number: str) -> Optional[str]:
        """Obter contexto da conversa do usuário"""
        try:
            if not self.pool:
                return None
            
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT context FROM conversations 
                    WHERE phone_number = $1 AND status = 'active'
                    ORDER BY last_activity DESC LIMIT 1
                """, phone_number)
                
                return result['context'] if result else None
                
        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return None
    
    async def update_user_context(self, phone_number: str, context: str):
        """Atualizar contexto da conversa"""
        try:
            if not self.pool:
                return
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversations (phone_number, context)
                    VALUES ($1, $2)
                    ON CONFLICT (phone_number) DO UPDATE SET 
                        context = $2, 
                        last_activity = CURRENT_TIMESTAMP
                """, phone_number, context)
                
        except Exception as e:
            logger.error(f"Error updating user context: {str(e)}")
    
    async def get_recent_messages(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """Obter mensagens recentes do usuário"""
        try:
            if not self.pool:
                return []
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT message_text, message_type, created_at
                    FROM messages 
                    WHERE phone_number = $1
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, phone_number, limit)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting recent messages: {str(e)}")
            return []
    
    async def check_connection(self) -> bool:
        """Verificar conexão com banco"""
        try:
            if not self.pool:
                if self.database_url:
                    await self.init_pool()
                else:
                    return False
            
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
                
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False
    
    async def close(self):
        """Fechar pool de conexões"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
