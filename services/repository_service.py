# services/repository_service.py
import logging
from api.supabase_client import SupabaseClient
from repositories.user_repository import UserRepository
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from repositories.credit_repository import CreditRepository

logger = logging.getLogger(__name__)

class RepositoryService:
    """Centralny serwis zapewniający dostęp do wszystkich repozytoriów"""
    
    def __init__(self, supabase_client: SupabaseClient):
        self.user_repository = UserRepository(supabase_client)
        self.conversation_repository = ConversationRepository(supabase_client)
        self.message_repository = MessageRepository(supabase_client)
        self.credit_repository = CreditRepository(supabase_client)
        
        logger.info("Serwis Repozytorium zainicjalizowany")