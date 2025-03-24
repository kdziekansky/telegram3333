# services/api_service.py
import logging
from typing import Dict, List, AsyncGenerator
from api.openai_client import OpenAIClient
from api.supabase_client import SupabaseClient
from config import OPENAI_API_KEY, DEFAULT_MODEL, SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

class APIService:
    """Centralny serwis API zapewniający dostęp do wszystkich zewnętrznych API"""
    
    def __init__(self):
        self.openai = OpenAIClient(api_key=OPENAI_API_KEY)
        self.supabase = SupabaseClient(url=SUPABASE_URL, key=SUPABASE_KEY)
        
        logger.info("Serwis API zainicjalizowany")
    
    # Metody API OpenAI
    async def chat_completion_text(self, messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> str:
        """Generuje odpowiedź czatu i zwraca tekst"""
        return await self.openai.chat_completion_text(messages, model)
    
    async def chat_completion_stream(self, messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> AsyncGenerator[str, None]:
        """Generuje strumieniową odpowiedź czatu"""
        async for chunk in self.openai.chat_completion_stream(messages, model):
            yield chunk
    
    async def generate_image(self, prompt: str) -> str:
        """Generuje obraz za pomocą DALL-E"""
        return await self.openai.generate_image(prompt)