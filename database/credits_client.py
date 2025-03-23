"""
Moduł do zarządzania kredytami użytkowników - adapter dla Supabase
Przekierowuje wszystkie wywołania do implementacji Supabase
"""
import logging
from database.supabase_client import (
    get_user_credits as supabase_get_user_credits,
    add_user_credits as supabase_add_user_credits,
    deduct_user_credits as supabase_deduct_user_credits,
    check_user_credits as supabase_check_user_credits,
    get_credit_packages as supabase_get_credit_packages,
    get_package_by_id as supabase_get_package_by_id,
    purchase_credits as supabase_purchase_credits,
    get_user_credit_stats as supabase_get_user_credit_stats,
    add_stars_payment_option as supabase_add_stars_payment_option
)

logger = logging.getLogger(__name__)

# Ścieżka do pliku bazy danych - zachowana dla kompatybilności
DB_PATH = "bot_database.sqlite"

def get_user_credits(user_id):
    """
    Pobiera liczbę kredytów użytkownika
    
    Args:
        user_id (int): ID użytkownika
    
    Returns:
        int: Liczba kredytów lub 0, jeśli nie znaleziono
    """
    return supabase_get_user_credits(user_id)

def add_user_credits(user_id, amount, description=None):
    """
    Dodaje kredyty do konta użytkownika
    
    Args:
        user_id (int): ID użytkownika
        amount (int): Liczba kredytów do dodania
        description (str, optional): Opis transakcji
    
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    return supabase_add_user_credits(user_id, amount, description)

def deduct_user_credits(user_id, amount, description=None):
    """
    Odejmuje kredyty z konta użytkownika
    
    Args:
        user_id (int): ID użytkownika
        amount (int): Liczba kredytów do odjęcia
        description (str, optional): Opis transakcji
    
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    return supabase_deduct_user_credits(user_id, amount, description)

def check_user_credits(user_id, amount_needed):
    """
    Sprawdza, czy użytkownik ma wystarczającą liczbę kredytów
    
    Args:
        user_id (int): ID użytkownika
        amount_needed (int): Wymagana liczba kredytów
    
    Returns:
        bool: True jeśli użytkownik ma wystarczającą liczbę kredytów, False w przeciwnym razie
    """
    return supabase_check_user_credits(user_id, amount_needed)

def get_credit_packages():
    """
    Pobiera dostępne pakiety kredytów
    
    Returns:
        list: Lista słowników z informacjami o pakietach lub pusta lista w przypadku błędu
    """
    return supabase_get_credit_packages()

def get_package_by_id(package_id):
    """
    Pobiera informacje o pakiecie kredytów
    
    Args:
        package_id (int): ID pakietu
    
    Returns:
        dict: Słownik z informacjami o pakiecie lub None w przypadku błędu
    """
    return supabase_get_package_by_id(package_id)

def purchase_credits(user_id, package_id):
    """
    Dokonuje zakupu kredytów
    
    Args:
        user_id (int): ID użytkownika
        package_id (int): ID pakietu
    
    Returns:
        tuple: (success, package) gdzie success to bool, a package to słownik z informacjami o pakiecie
    """
    return supabase_purchase_credits(user_id, package_id)

def get_user_credit_stats(user_id):
    """
    Pobiera statystyki kredytów użytkownika
    
    Args:
        user_id (int): ID użytkownika
    
    Returns:
        dict: Słownik z informacjami o kredytach użytkownika
    """
    return supabase_get_user_credit_stats(user_id)

def add_stars_payment_option(user_id, stars_amount, credits_amount, description=None):
    """
    Dodaje kredyty do konta użytkownika za płatność gwiazdkami
    
    Args:
        user_id (int): ID użytkownika
        stars_amount (int): Liczba gwiazdek
        credits_amount (int): Liczba kredytów do dodania
        description (str, optional): Opis transakcji
    
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    return supabase_add_stars_payment_option(user_id, stars_amount, credits_amount, description)

def get_stars_conversion_rate():
    """
    Pobiera aktualny kurs wymiany gwiazdek na kredyty
    
    Returns:
        dict: Słownik z kursami wymiany dla różnych ilości gwiazdek
    """
    # Ta funkcja nie ma odpowiednika w supabase_client.py, więc zachowujemy oryginalną implementację
    return {
        1: 10,    # 1 gwiazdka = 10 kredytów
        5: 55,    # 5 gwiazdek = 55 kredytów (10% bonus)
        10: 120,  # 10 gwiazdek = 120 kredytów (20% bonus)
        25: 325,  # 25 gwiazdek = 325 kredytów (30% bonus)
        50: 700   # 50 gwiazdek = 700 kredytów (40% bonus)
    }