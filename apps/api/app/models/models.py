from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class WhatsAppMessage:
    """Modelo para mensagens do WhatsApp"""
    id: str
    from_number: str
    text: str
    timestamp: datetime
    message_type: str = "text"
    
@dataclass
class User:
    """Modelo para usuários"""
    phone_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    
@dataclass
class Conversation:
    """Modelo para conversas"""
    phone_number: str
    context: str
    last_activity: datetime
    status: str = "active"
