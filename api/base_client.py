# api/base_client.py
import logging
import time
import asyncio
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger(__name__)

class APIClient:
    """Bazowa klasa dla klientów API z wspólną funkcjonalnością"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def _request_with_retry(self, request_func, *args, **kwargs) -> Any:
        """Wykonuje żądanie z logiką ponawiania"""
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            try:
                # Rozróżnienie między funkcjami sync i async
                if asyncio.iscoroutinefunction(request_func):
                    return await request_func(*args, **kwargs)
                else:
                    # Dla funkcji synchronicznych nie używamy await
                    return request_func(*args, **kwargs)
            except Exception as e:
                retries += 1
                last_error = e
                logger.warning(f"Żądanie API nie powiodło się (próba {retries}/{self.max_retries}): {str(e)}")
                
                if retries < self.max_retries:
                    sleep_time = self.retry_delay * (2 ** (retries - 1))
                    logger.info(f"Ponowna próba za {sleep_time:.2f} sekund...")
                    await asyncio.sleep(sleep_time)
                    
        logger.error(f"Żądanie API nie powiodło się po {self.max_retries} próbach: {str(last_error)}")
        raise last_error