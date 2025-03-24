# api/openai_client.py
import asyncio
import time
import logging
from typing import List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from api.base_client import APIClient
from config import OPENAI_API_KEY, DEFAULT_MODEL, DALL_E_MODEL

logger = logging.getLogger(__name__)

class OpenAIClient(APIClient):
    """Klient API OpenAI z obsługą błędów i ponawianiem"""
    
    def __init__(self, api_key: str = OPENAI_API_KEY, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(max_retries, retry_delay)
        from httpx import AsyncClient
        http_client = AsyncClient()
        self.client = AsyncOpenAI(api_key=api_key, http_client=http_client)
        logger.info(f"Klient OpenAI zainicjalizowany z kluczem API: {'ważny' if api_key else 'brak'}")
    
    async def chat_completion(self, messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, stream: bool = False, **kwargs) -> Any:
        """Generuje odpowiedź czatu z API OpenAI"""
        try:
            if "gpt-4" in model and not stream:
                await asyncio.sleep(0.5)
                
            return await self._request_with_retry(
                self.client.chat.completions.create,
                model=model,
                messages=messages,
                stream=stream,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Błąd API OpenAI: {str(e)}")
            raise
    
    async def chat_completion_text(self, messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, **kwargs) -> str:
        """Generuje odpowiedź czatu i zwraca tekst"""
        response = await self.chat_completion(messages, model, stream=False, **kwargs)
        return response.choices[0].message.content
    
    async def chat_completion_stream(self, messages: List[Dict[str, str]], model: str = DEFAULT_MODEL, **kwargs) -> AsyncGenerator[str, None]:
        """Generuje strumieniową odpowiedź czatu"""
        stream = await self.chat_completion(messages, model, stream=True, **kwargs)
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def generate_image(self, prompt: str, model: str = DALL_E_MODEL, size: str = "1024x1024", n: int = 1, **kwargs) -> str:
        """Generuje obraz za pomocą DALL-E"""
        try:
            response = await self._request_with_retry(
                self.client.images.generate,
                model=model,
                prompt=prompt,
                n=n,
                size=size,
                **kwargs
            )
            return response.data[0].url
        except Exception as e:
            logger.error(f"Błąd generowania obrazu: {str(e)}")
            raise