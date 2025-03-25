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
    
    async def update(self, conversation: Conversation) -> Conversation:
        """Aktualizuje istniejącą konwersację"""
        try:
            conversation_data = {
                "user_id": conversation.user_id,
                "last_message_at": datetime.now(pytz.UTC).isoformat()
            }
            
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
    
    async def get_active_conversation(self, user_id: int):
        """Pobiera aktywną konwersację dla użytkownika w formie słownika"""
        try:
            filters = {"user_id": user_id}
            
            result = await self.client.query(
                self.table, 
                query_type="select",
                filters=filters,
                order_by="-last_message_at", 
                limit=1
            )
            
            if result:
                # Zwracamy bezpośrednio słownik wyniku
                return result[0]
            
            # Jeśli nie znaleziono konwersacji, utwórz nową
            return await self.create_new_conversation(user_id)
        except Exception as e:
            logger.error(f"Błąd pobierania aktywnej konwersacji dla użytkownika {user_id}: {e}")
            # Próba utworzenia nowej konwersacji
            return await self.create_new_conversation(user_id)

    async def create_new_conversation(self, user_id: int):
        """Tworzy nową konwersację dla użytkownika i zwraca słownik"""
        try:
            now = datetime.now(pytz.UTC).isoformat()
            
            conversation_data = {
                "user_id": user_id,
                "created_at": now,
                "last_message_at": now
            }
            
            result = await self.client.query(
                self.table, 
                query_type="insert",
                data=conversation_data
            )
            
            if result:
                return result[0]  # Zwracamy surowy słownik
            raise Exception("Błąd tworzenia konwersacji - brak odpowiedzi")
        except Exception as e:
            logger.error(f"Błąd tworzenia nowej konwersacji dla użytkownika {user_id}: {e}")
            raise
            
    async def create_new_conversation(self, user_id: int) -> Conversation:
        """Tworzy nową konwersację dla użytkownika"""
        try:
            # Utwórz nową konwersację
            new_conversation = Conversation(user_id=user_id)
            return await self.create(new_conversation)
        except Exception as e:
            logger.error(f"Błąd tworzenia nowej konwersacji dla użytkownika {user_id}: {e}")
            # Fallback - spróbuj utworzyć podstawowy obiekt
            try:
                now = datetime.now(pytz.UTC).isoformat()
                conversation_data = {
                    "user_id": user_id,
                    "created_at": now,
                    "last_message_at": now
                }
                
                result = await self.client.query(
                    self.table, 
                    query_type="insert",
                    data=conversation_data
                )
                
                logger.info(f"Fallback: Utworzono konwersację dla {user_id} bez Conversation.from_dict")
                
                # Ręcznie utwórz obiekt Conversation
                response = Conversation(
                    id=result[0].get('id'),
                    user_id=user_id,
                    created_at=datetime.fromisoformat(result[0].get('created_at').replace('Z', '+00:00')),
                    last_message_at=datetime.fromisoformat(result[0].get('last_message_at').replace('Z', '+00:00'))
                )
                return response
            except Exception as e2:
                logger.error(f"Fallback tworzenia konwersacji również zawiódł: {e2}")
                raise e