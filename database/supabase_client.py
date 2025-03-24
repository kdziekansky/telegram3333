# database/supabase_client.py
from services.api_service import APIService
from services.repository_service import RepositoryService
from database.models import Conversation, Message
import logging
from database.credits_client import get_user_credits

# Utworzenie globalnych instancji
api_service = APIService()
repository_service = RepositoryService(api_service.supabase)

# Zmienne dla kompatybilności wstecznej
supabase = api_service.supabase.client  # Dla bezpośredniego dostępu, jeśli potrzebne
logger = logging.getLogger(__name__)

# Funkcje dla kompatybilności wstecznej
async def get_or_create_user(user_id, username=None, first_name=None, last_name=None, language_code=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.get_or_create(user_id, username, first_name, last_name, language_code)

async def get_active_conversation(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.get_active_conversation(user_id)

async def create_new_conversation(user_id, theme_id=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.create_new_conversation(user_id, theme_id)

async def save_message(conversation_id, user_id, content, is_from_user=True, model_used=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.message_repository.save_message(conversation_id, user_id, content, is_from_user, model_used)

async def get_conversation_history(conversation_id, limit=20):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.message_repository.get_conversation_history(conversation_id, limit)

async def increment_messages_used(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.increment_messages_used(user_id)

async def update_user_language(user_id, language):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.update_language(user_id, language)

async def check_active_subscription(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.check_active_subscription(user_id)

async def get_subscription_end_date(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.get_subscription_end_date(user_id)

async def get_message_status(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.user_repository.get_message_status(user_id)

async def activate_user_license(user_id, license_key):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.license_repository.activate_license(user_id, license_key)

async def get_credit_transactions(user_id, days=30):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.credit_repository.get_transactions(user_id, days)

async def get_credit_usage_by_type(user_id, days=30):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.credit_repository.get_usage_by_type(user_id, days)

async def get_user_credit_stats(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.credit_repository.get_user_stats(user_id)

async def create_conversation_theme(user_id, theme_name):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.create_theme(user_id, theme_name)

async def get_user_themes(user_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.get_user_themes(user_id)

async def get_theme_by_id(theme_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.get_theme_by_id(theme_id)

async def get_active_themed_conversation(user_id, theme_id):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.conversation_repository.get_active_themed_conversation(user_id, theme_id)

async def save_prompt_template(name, description, prompt_text):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.prompt_repository.save_template(name, description, prompt_text)

async def get_prompt_templates():
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.prompt_repository.get_templates()

async def create_license(duration_days, price):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.license_repository.create_license(duration_days, price)

async def use_activation_code(user_id, code):
    """Funkcja dla kompatybilności wstecznej"""
    return await repository_service.activation_repository.use_code(user_id, code)