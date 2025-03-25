# repositories/conversation_repository.py
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import pytz
from database.models import Conversation
from repositories.base_repository import BaseRepository
from api.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class ConversationRepository(BaseRepository[Conversation]):
    """Repozytorium dla operacji na konwersacjach"""
    
    def __init__(self, client: SupabaseClient):
        self.client = client
        self.table = "conversations"
    
    async def get_by_id(self, id: int) -> Optional[Conversation]:
        """Pobiera konwersację po ID"""
        try:
            result = await self.client.query(
                self.table, 
                query_type="select",
                filters={"id": id}
            )
            
            if result:
                return Conversation.from_dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Błąd pobierania konwersacji {id}: {e}")
            return None
    
    async def get_all(self) -> List[Conversation]:
        """Pobiera wszystkie konwersacje"""
        try:
            result = await self.client.query(self.table)
            return [Conversation.from_dict(data) for data in result]
        except Exception as e:
            logger.error(f"Błąd pobierania wszystkich konwersacji: {e}")
            return []
    
    async def create(self, conversation: Conversation) -> Conversation:
        """Tworzy nową konwersację"""
        try:
            now = datetime.now(pytz.UTC).isoformat()
            
            conversation_data = {
                "user_id": conversation.user_id,
                "created_at": now,
                "last_message_at": now
            }
            
            if hasattr(conversation, 'theme_id') and conversation.theme_id:
                conversation_data["theme_id"] = conversation.theme_id
            
            result = await self.client.query(
                self.table, 
                query_type="insert",
                data=conversation_data
            )
            
            if result:
                return Conversation.from_dict(result[0])
            raise Exception("Błąd tworzenia konwersacji - brak odpowiedzi")
        except Exception as e:
            logger.error(f"Błąd tworzenia konwersacji: {e}")
            raise

    async def create_new_conversation(self, user_id, theme_id=None):
        """Tworzy nową konwersację dla użytkownika"""
        try:
            from database.models import Conversation
            
            # Utwórz obiekt konwersacji
            new_conversation = Conversation(user_id=user_id)
            if theme_id:
                new_conversation.theme_id = theme_id
            
            # Użyj istniejącej metody create
            return await self.create(new_conversation)
        except Exception as e:
            logger.error(f"Błąd tworzenia nowej konwersacji dla użytkownika {user_id}: {e}")
            # Fallback - bezpośrednie użycie klienta
            try:
                now = datetime.now(pytz.UTC).isoformat()
                
                conversation_data = {
                    "user_id": user_id,
                    "created_at": now,
                    "last_message_at": now
                }
                
                if theme_id:
                    conversation_data["theme_id"] = theme_id
                
                result = await self.client.query(
                    self.table, 
                    query_type="insert",
                    data=conversation_data
                )
                
                if result:
                    return Conversation.from_dict(result[0])
                
                raise Exception("Błąd tworzenia konwersacji - brak odpowiedzi")
            except Exception as e2:
                logger.error(f"Fallback tworzenia konwersacji również zawiódł: {e2}")
                raise

    async def update(self, conversation: Conversation) -> Conversation:
        """Aktualizuje istniejącą konwersację"""
        try:
            conversation_data = {
                "user_id": conversation.user_id,
                "last_message_at": datetime.now(pytz.UTC).isoformat()
            }
            
            if hasattr(conversation, 'theme_id') and conversation.theme_id:
                conversation_data["theme_id"] = conversation.theme_id
            
            result = await self.client.query(
                self.table, 
                query_type="update",
                filters={"id": conversation.id},
                data=conversation_data
            )
            
            if result:
                return Conversation.from_dict(result[0])
            raise Exception(f"Błąd aktualizacji konwersacji {conversation.id} - brak odpowiedzi")
        except Exception as e:
            logger.error(f"Błąd aktualizacji konwersacji {conversation.id}: {e}")
            raise
    
    async def delete(self, id: int) -> bool:
        """Usuwa konwersację po ID"""
        try:
            result = await self.client.query(
                self.table,
                query_type="delete",
                filters={"id": id}
            )
            
            return bool(result)
        except Exception as e:
            logger.error(f"Błąd usuwania konwersacji {id}: {e}")
            return False
    
    async def get_active_conversation(self, user_id: int, theme_id: Optional[int] = None) -> Conversation:
        """Pobiera aktywną konwersację dla użytkownika"""
        try:
            filters = {"user_id": user_id}
            
            if theme_id:
                filters["theme_id"] = theme_id
            
            result = await self.client.query(
                self.table, 
                query_type="select",
                filters=filters,
                order_by="-last_message_at", 
                limit=1
            )
            
            if result:
                return Conversation.from_dict(result[0])
            
            # Jeśli nie znaleziono konwersacji, utwórz nową
            new_conversation = Conversation(user_id=user_id)
            
            if theme_id:
                new_conversation.theme_id = theme_id
            
            return await self.create(new_conversation)
        except Exception as e:
            logger.error(f"Błąd pobierania aktywnej konwersacji dla użytkownika {user_id}: {e}")
            # Utwórz nową konwersację jako awaryjną
            new_conversation = Conversation(user_id=user_id)
            
            if theme_id:
                new_conversation.theme_id = theme_id
            
            return await self.create(new_conversation)