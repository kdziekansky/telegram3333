# utils/openai_client.py
from services.api_service import APIService
import logging

logger = logging.getLogger(__name__)

# Utworzenie globalnej instancji
api_service = APIService()

# Funkcje kompatybilne ze starym kodem
async def chat_completion(messages, model=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await api_service.chat_completion_text(messages, model)

async def chat_completion_stream(messages, model=None):
    """Funkcja dla kompatybilności wstecznej"""
    async for chunk in api_service.chat_completion_stream(messages, model):
        yield chunk

async def generate_image_dall_e(prompt):
    """Funkcja dla kompatybilności wstecznej"""
    return await api_service.generate_image(prompt)

async def analyze_document(file_bytes, file_name, mode="analyze", target_language=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await api_service.document_service.analyze(file_bytes, file_name, mode, target_language)

async def analyze_image(file_bytes, file_name, mode="analyze", target_language=None):
    """Funkcja dla kompatybilności wstecznej"""
    return await api_service.document_service.analyze_image(file_bytes, file_name, mode, target_language)

def prepare_messages_from_history(history, user_message, system_prompt):
    """Funkcja dla kompatybilności wstecznej"""
    messages = [{"role": "system", "content": system_prompt}]
    
    # Dodaj historię konwersacji
    for msg in history:
        role = "user" if msg.get("is_from_user", False) else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
    
    # Dodaj bieżącą wiadomość użytkownika
    messages.append({"role": "user", "content": user_message})
    
    return messages