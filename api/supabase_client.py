# api/supabase_client.py
import logging
from typing import Dict, List, Any, Optional
from supabase import create_client
from api.base_client import APIClient

logger = logging.getLogger(__name__)

class SupabaseClient(APIClient):
    """Klient API Supabase z obsługą błędów i ponawianiem"""
    
    def __init__(self, url: str, key: str, max_retries: int = 3, retry_delay: float = 1.0):
        super().__init__(max_retries, retry_delay)
        
        try:
            self.client = create_client(url, key)
            logger.info("Pomyślnie zainicjalizowano klienta Supabase")
        except Exception as e:
            logger.error(f"Błąd inicjalizacji klienta Supabase: {e}")
            self.client = self._create_dummy_client()
    
    def _create_dummy_client(self) -> Any:
        """Tworzy zastępczy klient dla płynnej degradacji"""
        class DummyClient:
            def table(self, *args, **kwargs): return self
            def select(self, *args, **kwargs): return self
            def insert(self, *args, **kwargs): return self
            def update(self, *args, **kwargs): return self
            def delete(self, *args, **kwargs): return self
            def eq(self, *args, **kwargs): return self
            def order(self, *args, **kwargs): return self
            def limit(self, *args, **kwargs): return self
            def execute(self, *args, **kwargs):
                logger.warning("Używam zastępczego klienta Supabase - brak połączenia z bazą danych")
                return type('obj', (object,), {'data': []})
        
        return DummyClient()
    
    async def query(self, table: str, query_type: str = "select", 
                   columns: str = "*", filters: Optional[Dict] = None,
                   data: Optional[Dict] = None, order_by: Optional[str] = None,
                   limit: Optional[int] = None) -> List:
        """Wykonuje zapytanie do Supabase"""
        query = self.client.table(table)
        
        # Budowanie zapytania
        if query_type == "select":
            query = query.select(columns)
        elif query_type == "insert" and data:
            query = query.insert(data)
        elif query_type == "update" and data:
            query = query.update(data)
        elif query_type == "delete":
            query = query.delete()
        
        # Stosowanie filtrów
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        # Stosowanie sortowania
        if order_by:
            desc = order_by.startswith("-")
            field = order_by[1:] if desc else order_by
            query = query.order(field, desc=desc)
        
        # Stosowanie limitu
        if limit:
            query = query.limit(limit)
        
        try:
            # Poprawione: używamy _execute_query_sync zamiast _execute_query
            response = await self._request_with_retry(self._execute_query_sync, query)
            return response.data
        except Exception as e:
            logger.error(f"Błąd zapytania Supabase: {e}")
            return []
    
    # Nowa metoda, która wykonuje zapytanie synchronicznie (bez await)
    def _execute_query_sync(self, query):
        """Wykonuje zapytanie synchronicznie - bez użycia await"""
        return query.execute()