"""
Moduł do zarządzania kodami aktywacyjnymi - adapter dla Supabase
"""
import logging
from database.supabase_client import (
    create_activation_code as supabase_create_activation_code,
    use_activation_code as supabase_use_activation_code
)

logger = logging.getLogger(__name__)

def generate_activation_code(length=8):
    """Funkcja pomocnicza do generowania kodu - zachowana dla kompatybilności"""
    # Ta funkcja jest prawdopodobnie wywoływana wewnętrznie przez create_activation_code w Supabase
    # Możemy zostawić implementację pustą, gdyż nie będzie używana
    pass

def create_activation_code(credits):
    """Tworzy nowy kod aktywacyjny dla określonej liczby kredytów"""
    return supabase_create_activation_code(credits)

def create_multiple_codes(credits, count=1):
    """Tworzy wiele kodów aktywacyjnych"""
    codes = []
    for _ in range(count):
        code = create_activation_code(credits)
        if code:
            codes.append(code)
    return codes

def activate_code(user_id, code):
    """Aktywuje kod dla użytkownika"""
    return supabase_use_activation_code(user_id, code)

def get_code_info(code):
    """Pobiera informacje o kodzie - funkcja może nie mieć odpowiednika w Supabase"""
    # Implementację możemy dodać później jeśli potrzebna
    pass

def bulk_create_activation_codes(credits_values, count_per_value=10):
    """Tworzy wiele kodów o różnych wartościach"""
    result = {}
    for credits in credits_values:
        codes = create_multiple_codes(credits, count_per_value)
        result[credits] = codes
    return result