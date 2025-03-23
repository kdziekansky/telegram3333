"""
Moduł do zarządzania licencjami
"""
import uuid
import datetime
import pytz
import logging
from config import SUBSCRIPTION_PLANS
from database.supabase_client import create_license, activate_user_license

logger = logging.getLogger(__name__)

def generate_license_key():
    """
    Generuje unikalny klucz licencyjny
    
    Returns:
        str: Unikalny klucz licencyjny
    """
    return str(uuid.uuid4())

def create_new_license(duration_days, quantity=1):
    """
    Tworzy nową licencję o określonym czasie trwania
    
    Args:
        duration_days (int): Czas trwania licencji w dniach
        quantity (int, optional): Ilość licencji do wygenerowania. Domyślnie 1.
    
    Returns:
        list: Lista wygenerowanych kluczy licencyjnych
    """
    if duration_days not in SUBSCRIPTION_PLANS:
        logger.error(f"Nieprawidłowy czas trwania licencji: {duration_days}")
        return []
    
    price = SUBSCRIPTION_PLANS[duration_days]["price"]
    license_keys = []
    
    for _ in range(quantity):
        license_data = create_license(duration_days, price)
        if license_data:
            license_keys.append(license_data["license_key"])
        else:
            logger.error("Błąd podczas tworzenia licencji")
    
    return license_keys

def activate_license_for_user(user_id, license_key):
    """
    Aktywuje licencję dla użytkownika
    
    Args:
        user_id (int): ID użytkownika
        license_key (str): Klucz licencyjny
    
    Returns:
        tuple: (Czy aktywacja się powiodła, Data końca subskrypcji)
    """
    return activate_user_license(user_id, license_key)

def get_subscription_details(end_date):
    """
    Pobiera szczegóły subskrypcji
    
    Args:
        end_date (datetime): Data końca subskrypcji
    
    Returns:
        dict: Szczegóły subskrypcji
    """
    if not end_date:
        return {
            "active": False,
            "end_date": None,
            "days_left": 0,
            "status": get_text("subscription_inactive", language)
        }
    
    now = datetime.datetime.now(pytz.UTC)
    days_left = (end_date - now).days
    
    return {
        "active": days_left > 0,
        "end_date": end_date,
        "days_left": max(0, days_left),
        "status": get_text("subscription_active", language) if days_left > 0 else get_text("subscription_expired_status", language)
    }

def validate_license_key(license_key):
    """
    Sprawdza, czy klucz licencyjny ma prawidłowy format
    
    Args:
        license_key (str): Klucz licencyjny do sprawdzenia
    
    Returns:
        bool: Czy klucz ma prawidłowy format
    """
    try:
        # Sprawdź czy klucz jest poprawnym UUID
        uuid_obj = uuid.UUID(license_key)
        return str(uuid_obj) == license_key
    except (ValueError, AttributeError):
        return False