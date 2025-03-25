# api/anthropic_client.py
import asyncio
import time
import logging
from typing import List, Dict, Any, AsyncGenerator
from api.base_client import APIClient
from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

class AnthropicClient(APIClient):
    """Klient API Anthropic (Claude) z obsługą błędów i ponawianiem"""
    
    def __init__(self, api_key: str = ANTHROPIC_API_KEY, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(max_retries, retry_delay)
        from httpx import AsyncClient
        from anthropic import AsyncAnthropic
        
        self.client = AsyncAnthropic(api_key=api_key)
        logger.info(f"Klient Anthropic zainicjalizowany z kluczem API: {'ważny' if api_key else 'brak'}")
    
    async def chat_completion(self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet", stream: bool = False, **kwargs) -> Any:
        """Generuje odpowiedź czatu z API Anthropic"""
        try:
            # Konwersja formatu wiadomości z OpenAI na format Anthropic
            anthropic_messages = self._convert_to_anthropic_format(messages)
            
            # Wysyłanie zapytania
            return await self._request_with_retry(
                self._make_anthropic_request,
                model=model,
                messages=anthropic_messages,
                stream=stream,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Błąd API Anthropic: {str(e)}")
            raise
    
    async def _make_anthropic_request(self, model: str, messages: List[Dict], stream: bool = False, **kwargs):
        """Wykonuje właściwe zapytanie do API Anthropic"""
        max_tokens = kwargs.pop('max_tokens', 4096)
        temperature = kwargs.pop('temperature', 0.7)
        
        if stream:
            response = await self.client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            return response
        else:
            response = await self.client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response
    
    def _convert_to_anthropic_format(self, openai_messages: List[Dict[str, str]]) -> List[Dict]:
        """Konwertuje format wiadomości OpenAI na format Anthropic"""
        anthropic_messages = []
        
        # Pomijamy pierwszą wiadomość systemową - obsługujemy ją osobno
        system_message = None
        if openai_messages and openai_messages[0]['role'] == 'system':
            system_message = openai_messages[0]['content']
            openai_messages = openai_messages[1:]
        
        # Konwertuj pozostałe wiadomości
        for msg in openai_messages:
            role = "user" if msg['role'] == 'user' else "assistant"
            anthropic_messages.append({
                "role": role,
                "content": msg['content']
            })
        
        return anthropic_messages
    
    async def chat_completion_text(self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet", **kwargs) -> str:
        """Generuje odpowiedź czatu i zwraca tekst"""
        system_prompt = None
        if messages and messages[0]['role'] == 'system':
            system_prompt = messages[0]['content']
            messages = messages[1:]
            
        anthropic_messages = self._convert_to_anthropic_format(messages)
        
        response = await self.client.messages.create(
            model=model,
            messages=anthropic_messages,
            system=system_prompt,
            max_tokens=kwargs.pop('max_tokens', 4096),
            temperature=kwargs.pop('temperature', 0.7),
            **kwargs
        )
        
        return response.content[0].text
    
    async def chat_completion_stream(self, messages: List[Dict[str, str]], model: str = "claude-3-5-sonnet", **kwargs) -> AsyncGenerator[str, None]:
        """Generuje strumieniową odpowiedź czatu"""
        system_prompt = None
        if messages and messages[0]['role'] == 'system':
            system_prompt = messages[0]['content']
            messages = messages[1:]
            
        anthropic_messages = self._convert_to_anthropic_format(messages)
        
        stream = await self.client.messages.create(
            model=model,
            messages=anthropic_messages,
            system=system_prompt,
            max_tokens=kwargs.pop('max_tokens', 4096),
            temperature=kwargs.pop('temperature', 0.7),
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.delta.text:
                yield chunk.delta.text