# repositories/base_repository.py
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository class for common data operations"""
    
    def __init__(self, client):
        self.client = client
        self.table = None
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID"""
        raise NotImplementedError("Subclass must implement this method")
    
    async def get_all(self) -> List[T]:
        """Get all entities"""
        raise NotImplementedError("Subclass must implement this method")
    
    async def create(self, entity: T) -> T:
        """Create new entity"""
        raise NotImplementedError("Subclass must implement this method")
    
    async def update(self, entity: T) -> T:
        """Update existing entity"""
        raise NotImplementedError("Subclass must implement this method")
    
    async def delete(self, id: int) -> bool:
        """Delete entity by ID"""
        raise NotImplementedError("Subclass must implement this method")