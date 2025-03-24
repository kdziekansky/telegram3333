# repositories/user_repository.py
import logging
from typing import List, Optional
from database.models import User
from repositories.base_repository import BaseRepository
from api.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User]):
    """Repozytorium dla operacji na użytkownikach"""
    
    def __init__(self, client: SupabaseClient):
        self.client = client
        self.table = "users"
    
    async def get_by_id(self, id: int) -> Optional[User]:
        """Pobiera użytkownika po ID"""
        try:
            result = await self.client.select(self.table, filters={"id": id})
            if result:
                return User.from_dict(result[0])
            return None
        except Exception as e:
            logger.error(f"Błąd pobierania użytkownika po ID {id}: {e}")
            return None
    
    async def get_all(self) -> List[User]:
        """Pobiera wszystkich użytkowników"""
        try:
            result = await self.client.select(self.table)
            return [User.from_dict(data) for data in result]
        except Exception as e:
            logger.error(f"Błąd pobierania wszystkich użytkowników: {e}")
            return []
    
    async def create(self, user: User) -> User:
        """Tworzy nowego użytkownika"""
        try:
            user_data = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
                "is_active": user.is_active
            }
            
            result = await self.client.insert(self.table, user_data)
            return User.from_dict(result)
        except Exception as e:
            logger.error(f"Błąd tworzenia użytkownika: {e}")
            raise