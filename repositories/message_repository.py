# repositories/message_repository.py
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import pytz
from database.models import Message
from repositories.base_repository import BaseRepository
from api.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class MessageRepository(BaseRepository[Message]):
    """Repozytorium dla operacji na wiadomościach"""
    
    def __init__(self, client: SupabaseClient):
        self.client = client
        self.table = "messages"
    
    async def get_by_id(self, id: int) -> Optional[Message]:
        """Pobiera wiadomość po ID"""
        try:
            result = await self.client.query(
                self.table, 
                query_type="select",
                filters={"id": id}
            )
            
            if result:
                return Message.from_dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Błąd pobierania wiadomości {id}: {e}")
            return None
    
    async def get_all(self) -> List[Message]:
        """Pobiera wszystkie wiadomości"""
        try:
            result = await self.client.query(self.table)
            return [Message.from_dict(data) for data in result]
        except Exception as e:
            logger.error(f"Błąd pobierania wszystkich wiadomości: {e}")
            return []
    
    async def create(self, message: Message) -> Message:
        """Tworzy nową wiadomość"""
        try:
            message_data = {
                "conversation_id": message.conversation_id,
                "user_id": message.user_id,
                "content": message.content,
                "is_from_user": message.is_from_user,
                "created_at": datetime.now(pytz.UTC).isoformat()
            }
            
            if message.model_used:
                message_data["model_used"] = message.model_used
            
            result = await self.client.query(
                self.table, 
                query_type="insert",
                data=message_data
            )
            
            if result:
                return Message.from_dict(result[0])
            raise Exception("Błąd tworzenia wiadomości - brak odpowiedzi")
        except Exception as e:
            logger.error(f"Błąd tworzenia wiadomości: {e}")
            raise
    
    async def update(self, message: Message) -> Message:
        """Aktualizuje istniejącą wiadomość"""
        try:
            message_data = {
                "content": message.content,
                "is_from_user": message.is_from_user
            }
            
            if message.model_used:
                message_data["model_used"] = message.model_used
            
            result = await self.client.query(
                self.table, 
                query_type="update",
                filters={"id": message.id},
                data=message_data
            )
            
            if result:
                return Message.from_dict(result[0])
            raise Exception(f"Błąd aktualizacji wiadomości {message.id} - brak odpowiedzi")
        except Exception as e:
            logger.error(f"Błąd aktualizacji wiadomości {message.id}: {e}")
            raise
    
    async def delete(self, id: int) -> bool:
        """Usuwa wiadomość po ID"""
        try:
            result = await self.client.query(
                self.table,
                query_type="delete",
                filters={"id": id}
            )
            
            return bool(result)
        except Exception as e:
            logger.error(f"Błąd usuwania wiadomości {id}: {e}")
            return False
    
    async def get_conversation_history(self, conversation_id: int, limit: int = 20) -> List[Message]:
        """Pobiera historię wiadomości dla konwersacji"""
        try:
            result = await self.client.query(
                self.table, 
                query_type="select",
                filters={"conversation_id": conversation_id},
                order_by="created_at", 
                limit=limit
            )
            
            return [Message.from_dict(data) for data in result]
        except Exception as e:
            logger.error(f"Błąd pobierania historii konwersacji {conversation_id}: {e}")
            return []
    
    async def save_message(self, conversation_id: int, user_id: int, content: str, 
                         is_from_user: bool, model_used: Optional[str] = None) -> Optional[Message]:
        """Zapisuje wiadomość do bazy danych"""
        try:
            message = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                content=content,
                is_from_user=is_from_user,
                model_used=model_used
            )
            
            return await self.create(message)
        except Exception as e:
            logger.error(f"Błąd zapisywania wiadomości: {e}")
            return None