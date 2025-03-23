"""
Moduł do zarządzania płatnościami - adapter dla Supabase
"""
import logging
import os
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# URL do funkcji Edge Functions w Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'mypremium_bot')

def get_available_payment_methods(user_language: str) -> List[Dict[str, Any]]:
    """
    Pobiera dostępne metody płatności dla określonego języka użytkownika
    
    Args:
        user_language (str): Język użytkownika (pl, en, ru)
    
    Returns:
        List[Dict]: Lista metod płatności dostępnych dla użytkownika
    """
    try:
        # Określ, które metody są dostępne na podstawie języka
        language_filter = ''
        if user_language == 'pl':
            language_filter = 'is_available_pl'
        elif user_language == 'en':
            language_filter = 'is_available_en'
        elif user_language == 'ru':
            language_filter = 'is_available_ru'
        else:
            language_filter = 'is_available_pl'  # domyślnie pl
            
        # Pobierz metody płatności z Supabase
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/payment_methods?select=*&{language_filter}=eq.true&is_active=eq.true",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Błąd podczas pobierania metod płatności: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Wyjątek podczas pobierania metod płatności: {e}")
        return []

def create_payment_url(
    user_id: int, 
    package_id: int, 
    payment_method_code: str, 
    is_subscription: bool = False
) -> Tuple[bool, str]:
    """
    Tworzy URL do płatności dla określonej metody płatności
    
    Args:
        user_id (int): ID użytkownika
        package_id (int): ID pakietu kredytów
        payment_method_code (str): Kod metody płatności
        is_subscription (bool): Czy to jest subskrypcja
    
    Returns:
        Tuple[bool, str]: (Czy operacja się powiodła, URL do płatności lub komunikat błędu)
    """
    try:
        # Obsługa różnych metod płatności
        if payment_method_code == 'stripe':
            return create_stripe_payment(user_id, package_id, is_subscription=False)
        elif payment_method_code == 'stripe_subscription':
            return create_stripe_payment(user_id, package_id, is_subscription=True)
        elif payment_method_code in ['allegro', 'russia_payment']:
            # Dla metod zewnętrznych pobierz URL z bazy danych
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/payment_methods?code=eq.{payment_method_code}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            
            if response.status_code == 200 and response.json():
                payment_method = response.json()[0]
                if payment_method['external_url']:
                    return True, payment_method['external_url']
                else:
                    return False, "Brak URL dla tej metody płatności."
            else:
                return False, "Nie znaleziono metody płatności."
        else:
            return False, "Nieobsługiwana metoda płatności."
    except Exception as e:
        logger.error(f"Wyjątek podczas tworzenia URL płatności: {e}")
        return False, f"Wystąpił błąd: {str(e)}"

def create_stripe_payment(user_id: int, package_id: int, is_subscription: bool = False) -> Tuple[bool, str]:
    """
    Tworzy sesję płatności Stripe
    
    Args:
        user_id (int): ID użytkownika
        package_id (int): ID pakietu kredytów
        is_subscription (bool): Czy to jest subskrypcja
    
    Returns:
        Tuple[bool, str]: (Czy operacja się powiodła, URL do płatności lub komunikat błędu)
    """
    try:
        # Definiujemy URL sukcesu i anulowania
        base_url = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start="
        success_url = f"{base_url}payment_success_{user_id}"
        cancel_url = f"{base_url}payment_cancel_{user_id}"
        
        # Wybierz odpowiednią Edge Function w zależności od typu płatności
        function_name = "stripe-subscription" if is_subscription else "stripe-payment"
        
        # Wywołaj Edge Function
        response = requests.post(
            f"{SUPABASE_URL}/functions/v1/{function_name}",
            json={
                "user_id": user_id,
                "package_id": package_id,
                "success_url": success_url,
                "cancel_url": cancel_url
            },
            headers={
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'url' in data:
                return True, data['url']
            else:
                return False, "Błąd: brak URL w odpowiedzi."
        else:
            return False, f"Błąd podczas tworzenia sesji płatności: {response.text}"
    except Exception as e:
        logger.error(f"Wyjątek podczas tworzenia sesji płatności Stripe: {e}")
        return False, f"Wystąpił błąd: {str(e)}"

def get_user_subscriptions(user_id: int) -> List[Dict[str, Any]]:
    """
    Pobiera aktywne subskrypcje użytkownika
    
    Args:
        user_id (int): ID użytkownika
    
    Returns:
        List[Dict]: Lista aktywnych subskrypcji
    """
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscriptions?user_id=eq.{user_id}&status=eq.active",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Błąd podczas pobierania subskrypcji: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Wyjątek podczas pobierania subskrypcji: {e}")
        return []

def cancel_subscription(subscription_id: int) -> bool:
    """
    Anuluje subskrypcję użytkownika
    
    Args:
        subscription_id (int): ID subskrypcji w bazie danych
    
    Returns:
        bool: Czy udało się anulować subskrypcję
    """
    try:
        # Pobierz dane subskrypcji
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscriptions?id=eq.{subscription_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code != 200 or not response.json():
            logger.error(f"Nie znaleziono subskrypcji o ID {subscription_id}")
            return False
        
        subscription = response.json()[0]
        external_subscription_id = subscription['external_subscription_id']
        
        # Anuluj subskrypcję w Stripe
        if subscription['payment_method_id'] in [1, 2]:  # Stripe lub Stripe Subskrypcja
            # Wywołaj Edge Function do anulowania subskrypcji
            cancel_response = requests.post(
                f"{SUPABASE_URL}/functions/v1/stripe-cancel-subscription",
                json={"subscription_id": external_subscription_id},
                headers={
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            
            if cancel_response.status_code != 200:
                logger.error(f"Błąd podczas anulowania subskrypcji w Stripe: {cancel_response.text}")
                return False
        
        # Aktualizuj status subskrypcji w bazie danych
        update_response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/subscriptions?id=eq.{subscription_id}",
            json={
                "status": "cancelled",
                "end_date": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
        )
        
        return update_response.status_code == 204
    except Exception as e:
        logger.error(f"Wyjątek podczas anulowania subskrypcji: {e}")
        return False

def get_payment_transactions(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Pobiera historię transakcji płatności użytkownika
    
    Args:
        user_id (int): ID użytkownika
        limit (int): Maksymalna liczba transakcji do pobrania
    
    Returns:
        List[Dict]: Lista transakcji
    """
    try:
        # Pobierz transakcje z Supabase
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/payment_transactions?user_id=eq.{user_id}&order=created_at.desc&limit={limit}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
        )
        
        if response.status_code == 200:
            transactions = response.json()
            
            # Pobierz dane pakietów i metod płatności
            packages_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/credit_packages",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            
            methods_response = requests.get(
                f"{SUPABASE_URL}/rest/v1/payment_methods",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                }
            )
            
            packages = {p['id']: p for p in packages_response.json()} if packages_response.status_code == 200 else {}
            methods = {m['id']: m for m in methods_response.json()} if methods_response.status_code == 200 else {}
            
            # Wzbogać dane transakcji
            for t in transactions:
                t['package_name'] = packages.get(t['credit_package_id'], {}).get('name', 'Nieznany pakiet')
                t['package_credits'] = packages.get(t['credit_package_id'], {}).get('credits', 0)
                t['payment_method_name'] = methods.get(t['payment_method_id'], {}).get('name', 'Nieznana metoda')
                t['payment_method_code'] = methods.get(t['payment_method_id'], {}).get('code', '')
            
            return transactions
        else:
            logger.error(f"Błąd podczas pobierania transakcji: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Wyjątek podczas pobierania transakcji: {e}")
        return []