"""
Definicje modeli danych dla bazy danych
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class User:
    """Model użytkownika"""
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    subscription_end_date: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Tworzy obiekt User z danych słownikowych"""
        # Konwersja pól datetime z ISO string
        if 'subscription_end_date' in data and data['subscription_end_date']:
            if isinstance(data['subscription_end_date'], str):
                data['subscription_end_date'] = datetime.fromisoformat(
                    data['subscription_end_date'].replace('Z', '+00:00')
                )
        
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(
                    data['created_at'].replace('Z', '+00:00')
                )
        
        return cls(**data)

@dataclass
class License:
    """Model licencji"""
    id: Optional[int] = None
    license_key: str = ""
    duration_days: int = 0
    price: float = 0.0
    is_used: bool = False
    used_at: Optional[datetime] = None
    used_by: Optional[int] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'License':
        """Tworzy obiekt License z danych słownikowych"""
        # Konwersja pól datetime z ISO string
        for date_field in ['used_at', 'created_at']:
            if date_field in data and data[date_field]:
                if isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace('Z', '+00:00')
                    )
        
        return cls(**data)

@dataclass
class Conversation:
    """Model konwersacji"""
    id: Optional[int] = None
    user_id: int = 0
    created_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Tworzy obiekt Conversation z danych słownikowych"""
        # Konwersja pól datetime z ISO string
        for date_field in ['created_at', 'last_message_at']:
            if date_field in data and data[date_field]:
                if isinstance(data[date_field], str):
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace('Z', '+00:00')
                    )
        
        return cls(**data)

@dataclass
class Message:
    """Model wiadomości"""
    id: Optional[int] = None
    conversation_id: int = 0
    user_id: int = 0
    content: str = ""
    is_from_user: bool = True
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Tworzy obiekt Message z danych słownikowych"""
        # Konwersja pól datetime z ISO string
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(
                    data['created_at'].replace('Z', '+00:00')
                )
        
        return cls(**data)

@dataclass
class PromptTemplate:
    """Model szablonu prompta"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    prompt_text: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """Tworzy obiekt PromptTemplate z danych słownikowych"""
        # Konwersja pól datetime z ISO string
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(
                    data['created_at'].replace('Z', '+00:00')
                )
        
        return cls(**data)