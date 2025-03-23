from supabase import create_client
import uuid
import datetime
import pytz
import logging
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# Inicjalizacja klienta Supabase
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Pomyślnie zainicjalizowano klienta Supabase")
except Exception as e:
    logger.error(f"Błąd inicjalizacji klienta Supabase: {e}")
    # Fallback - możemy utworzyć pustą klasę, która nie rzuci błędu
    class DummyClient:
        def table(self, *args, **kwargs):
            return self
        def select(self, *args, **kwargs):
            return self
        def insert(self, *args, **kwargs):
            return self
        def update(self, *args, **kwargs):
            return self
        def delete(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def order(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def execute(self, *args, **kwargs):
            logger.warning("Używanie dummy klienta Supabase - brak połączenia z bazą danych")
            return type('obj', (object,), {'data': []})
    
    supabase = DummyClient()

# Funkcje zarządzania użytkownikami
def get_or_create_user(user_id, username=None, first_name=None, last_name=None, language_code=None):
    """Pobierz lub utwórz użytkownika w bazie danych"""
    try:
        # Sprawdzamy czy użytkownik już istnieje
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if response.data:
            return response.data[0]
        
        # Jeśli nie istnieje, tworzymy nowego
        user_data = {
            'id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'language_code': language_code,
            'language': language_code,  # Domyślnie ustawiamy język interfejsu taki sam jak język klienta
            'created_at': datetime.datetime.now(pytz.UTC).isoformat(),
            'is_active': True,
            'messages_used': 0,
            'messages_limit': 0
        }
        
        response = supabase.table('users').insert(user_data).execute()
        
        if response.data:
            # Inicjalizacja rekordów kredytowych dla nowego użytkownika
            init_user_credits(user_id)
            return response.data[0]
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu/tworzeniu użytkownika: {e}")
    
    return None

def update_user_language(user_id, language):
    """Aktualizuje język użytkownika w bazie danych"""
    try:
        response = supabase.table('users').update({'language': language}).eq('id', user_id).execute()
        return True if response.data else False
    except Exception as e:
        logger.error(f"Błąd przy aktualizacji języka użytkownika: {e}")
        return False

# Funkcje obsługi kredytów
def init_user_credits(user_id):
    """Inicjalizuje rekord kredytów dla użytkownika"""
    try:
        credit_data = {
            'user_id': user_id,
            'credits_amount': 0,
            'total_credits_purchased': 0,
            'total_spent': 0
        }
        
        response = supabase.table('user_credits').insert(credit_data).execute()
        return True if response.data else False
    except Exception as e:
        logger.error(f"Błąd przy inicjalizacji kredytów użytkownika: {e}")
        return False

def get_user_credits(user_id):
    """Pobiera liczbę kredytów użytkownika"""
    try:
        response = supabase.table('user_credits').select('credits_amount').eq('user_id', user_id).execute()
        
        if response.data:
            return response.data[0]['credits_amount']
        
        # Jeśli nie znaleziono, zainicjuj rekord
        init_user_credits(user_id)
        return 0
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu kredytów użytkownika: {e}")
        return 0

def add_user_credits(user_id, amount, description=None):
    """Dodaje kredyty do konta użytkownika"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        # Pobierz aktualną liczbę kredytów
        response = supabase.table('user_credits').select('credits_amount').eq('user_id', user_id).execute()
        
        if response.data:
            current_credits = response.data[0]['credits_amount']
            
            # Aktualizuj istniejący rekord
            supabase.table('user_credits').update({
                'credits_amount': current_credits + amount,
                'total_credits_purchased': supabase.raw(f'total_credits_purchased + {amount}'),
                'last_purchase_date': now
            }).eq('user_id', user_id).execute()
        else:
            # Utwórz nowy rekord
            current_credits = 0
            init_user_credits(user_id)
            supabase.table('user_credits').update({
                'credits_amount': amount,
                'total_credits_purchased': amount,
                'last_purchase_date': now
            }).eq('user_id', user_id).execute()
        
        # Zapisz transakcję
        if amount != 0:  # Nie zapisujemy transakcji inicjalizujących z 0 kredytów
            supabase.table('credit_transactions').insert({
                'user_id': user_id,
                'transaction_type': 'add',
                'amount': amount,
                'credits_before': current_credits,
                'credits_after': current_credits + amount,
                'description': description,
                'created_at': now
            }).execute()
        
        return True
    except Exception as e:
        logger.error(f"Błąd przy dodawaniu kredytów użytkownika: {e}")
        return False

def deduct_user_credits(user_id, amount, description=None):
    """Odejmuje kredyty z konta użytkownika"""
    try:
        # Pobierz aktualną liczbę kredytów
        response = supabase.table('user_credits').select('credits_amount').eq('user_id', user_id).execute()
        
        if not response.data:
            return False
        
        current_credits = response.data[0]['credits_amount']
        
        # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
        if current_credits < amount:
            return False
        
        # Odejmij kredyty
        supabase.table('user_credits').update({
            'credits_amount': current_credits - amount
        }).eq('user_id', user_id).execute()
        
        # Zapisz transakcję
        now = datetime.datetime.now(pytz.UTC).isoformat()
        supabase.table('credit_transactions').insert({
            'user_id': user_id,
            'transaction_type': 'deduct',
            'amount': amount,
            'credits_before': current_credits,
            'credits_after': current_credits - amount,
            'description': description,
            'created_at': now
        }).execute()
        
        return True
    except Exception as e:
        logger.error(f"Błąd przy odejmowaniu kredytów użytkownika: {e}")
        return False

def check_user_credits(user_id, amount_needed):
    """Sprawdza, czy użytkownik ma wystarczającą liczbę kredytów"""
    current_credits = get_user_credits(user_id)
    return current_credits >= amount_needed

def get_credit_packages():
    """Pobiera dostępne pakiety kredytów"""
    try:
        response = supabase.table('credit_packages').select('*').eq('is_active', True).order('credits', desc=False).execute()
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu pakietów kredytów: {e}")
        return []

def get_package_by_id(package_id):
    """Pobiera informacje o pakiecie kredytów"""
    try:
        response = supabase.table('credit_packages').select('*').eq('id', package_id).eq('is_active', True).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu pakietu kredytów: {e}")
        return None

def purchase_credits(user_id, package_id):
    """Dokonuje zakupu kredytów"""
    try:
        # Pobierz informacje o pakiecie
        package = get_package_by_id(package_id)
        if not package:
            return False, None
        
        # Dodaj kredyty użytkownikowi
        now = datetime.datetime.now(pytz.UTC).isoformat()
        description = f"Zakup pakietu {package['name']}"
        
        # Pobierz aktualny stan kredytów
        response = supabase.table('user_credits').select('credits_amount').eq('user_id', user_id).execute()
        
        if response.data:
            current_credits = response.data[0]['credits_amount']
            
            # Aktualizuj rekord użytkownika
            supabase.table('user_credits').update({
                'credits_amount': current_credits + package['credits'],
                'total_credits_purchased': supabase.raw(f'total_credits_purchased + {package["credits"]}'),
                'last_purchase_date': now,
                'total_spent': supabase.raw(f'total_spent + {package["price"]}')
            }).eq('user_id', user_id).execute()
        else:
            # Jeśli rekord nie istnieje, utwórz go
            current_credits = 0
            init_user_credits(user_id)
            supabase.table('user_credits').update({
                'credits_amount': package['credits'],
                'total_credits_purchased': package['credits'],
                'last_purchase_date': now,
                'total_spent': package['price']
            }).eq('user_id', user_id).execute()
        
        # Zapisz transakcję
        supabase.table('credit_transactions').insert({
            'user_id': user_id,
            'transaction_type': 'purchase',
            'amount': package['credits'],
            'credits_before': current_credits,
            'credits_after': current_credits + package['credits'],
            'description': description,
            'created_at': now
        }).execute()
        
        return True, package
    except Exception as e:
        logger.error(f"Błąd przy zakupie kredytów: {e}")
        return False, None

def get_user_credit_stats(user_id):
    """Pobiera statystyki kredytów użytkownika"""
    try:
        # Pobierz podstawowe informacje o kredytach
        response = supabase.table('user_credits').select('*').eq('user_id', user_id).execute()
        
        if not response.data:
            return {
                'credits': 0,
                'total_purchased': 0,
                'last_purchase': None,
                'total_spent': 0.0,
                'usage_history': []
            }
        
        credit_info = response.data[0]
        
        # Pobierz historię ostatnich 10 transakcji
        transactions_response = supabase.table('credit_transactions').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(10).execute()
        
        usage_history = []
        for trans in transactions_response.data:
            usage_history.append({
                'type': trans['transaction_type'],
                'amount': trans['amount'],
                'balance': trans['credits_after'],
                'description': trans['description'],
                'date': trans['created_at']
            })
        
        return {
            'credits': credit_info['credits_amount'],
            'total_purchased': credit_info['total_credits_purchased'],
            'last_purchase': credit_info['last_purchase_date'],
            'total_spent': float(credit_info['total_spent']) if credit_info['total_spent'] else 0.0,
            'usage_history': usage_history
        }
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu statystyk kredytów użytkownika: {e}")
        return {
            'credits': 0,
            'total_purchased': 0,
            'last_purchase': None,
            'total_spent': 0.0,
            'usage_history': []
        }

def add_stars_payment_option(user_id, stars_amount, credits_amount, description=None):
    """Dodaje kredyty za płatność gwiazdkami"""
    if description is None:
        description = f"Zakup za {stars_amount} gwiazdek Telegram"
    
    return add_user_credits(user_id, credits_amount, description)

# Funkcje obsługi subskrypcji
def check_active_subscription(user_id):
    """Sprawdza czy użytkownik ma aktywną subskrypcję"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        # Sprawdź subskrypcję czasową
        response = supabase.table('users').select('subscription_end_date').eq('id', user_id).execute()
        
        if not response.data:
            return False
        
        user = response.data[0]
        end_date = user.get('subscription_end_date')
        
        if end_date:
            # Konwertujemy string na datę
            end_date = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            now_dt = datetime.datetime.now(pytz.UTC)
            
            if end_date > now_dt:
                return True
        
        # Sprawdź limit wiadomości
        return check_message_limit(user_id)
    except Exception as e:
        logger.error(f"Błąd przy sprawdzaniu subskrypcji: {e}")
        return False

def get_subscription_end_date(user_id):
    """Pobierz datę końca subskrypcji użytkownika"""
    try:
        response = supabase.table('users').select('subscription_end_date').eq('id', user_id).execute()
        
        if not response.data or not response.data[0].get('subscription_end_date'):
            return None
        
        end_date = response.data[0].get('subscription_end_date')
        
        # Konwertujemy string na datę
        return datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu daty końca subskrypcji: {e}")
        return None

def create_license(duration_days, price, message_limit=0):
    """Tworzy nową licencję"""
    try:
        license_key = str(uuid.uuid4())
        
        license_data = {
            'license_key': license_key,
            'duration_days': duration_days,
            'message_limit': message_limit,
            'price': price,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat()
        }
        
        response = supabase.table('licenses').insert(license_data).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu licencji: {e}")
        return None

def activate_user_license(user_id, license_key):
    """Aktywuje licencję dla użytkownika"""
    try:
        # Pobierz licencję
        response = supabase.table('licenses').select('*').eq('license_key', license_key).eq('is_used', False).execute()
        
        if not response.data:
            return False, None, 0
        
        license_data = response.data[0]
        
        # Pobierz obecny limit wiadomości użytkownika
        user_response = supabase.table('users').select('messages_limit, messages_used').eq('id', user_id).execute()
        
        if not user_response.data:
            return False, None, 0
        
        current_limit = user_response.data[0].get('messages_limit', 0)
        
        # Oblicz datę końca subskrypcji jeśli duration_days > 0
        now = datetime.datetime.now(pytz.UTC)
        end_date = None
        if license_data['duration_days'] > 0:
            end_date = now + datetime.timedelta(days=license_data['duration_days'])
        
        # Aktualizuj licencję
        supabase.table('licenses').update({
            'is_used': True,
            'used_at': now.isoformat(),
            'used_by': user_id
        }).eq('id', license_data['id']).execute()
        
        # Aktualizuj limity wiadomości użytkownika - dodaj nowe do istniejących
        new_message_limit = current_limit + license_data['message_limit']
        
        # Aktualizuj użytkownika
        if end_date:
            supabase.table('users').update({
                'subscription_end_date': end_date.isoformat(),
                'messages_limit': new_message_limit
            }).eq('id', user_id).execute()
        else:
            supabase.table('users').update({
                'messages_limit': new_message_limit
            }).eq('id', user_id).execute()
        
        return True, end_date, license_data['message_limit']
    except Exception as e:
        logger.error(f"Błąd przy aktywacji licencji: {e}")
        return False, None, 0

# Funkcje obsługi limitów wiadomości
def check_message_limit(user_id):
    """Sprawdza czy użytkownik ma dostępne wiadomości"""
    try:
        response = supabase.table('users').select('messages_limit, messages_used').eq('id', user_id).execute()
        
        if not response.data:
            return False
        
        user = response.data[0]
        message_limit = user.get('messages_limit', 0)
        messages_used = user.get('messages_used', 0)
        
        return messages_used < message_limit
    except Exception as e:
        logger.error(f"Błąd przy sprawdzaniu limitu wiadomości: {e}")
        return False

def increment_messages_used(user_id):
    """Zwiększa licznik wykorzystanych wiadomości"""
    try:
        # Pobierz aktualną liczbę wykorzystanych wiadomości
        response = supabase.table('users').select('messages_used').eq('id', user_id).execute()
        
        if not response.data:
            return False
        
        messages_used = response.data[0].get('messages_used', 0)
        messages_used += 1
        
        # Aktualizuj licznik
        supabase.table('users').update({
            'messages_used': messages_used
        }).eq('id', user_id).execute()
        
        return True
    except Exception as e:
        logger.error(f"Błąd przy aktualizacji licznika wiadomości: {e}")
        return False

def get_message_status(user_id):
    """Pobiera status wiadomości użytkownika"""
    try:
        response = supabase.table('users').select('messages_limit, messages_used').eq('id', user_id).execute()
        
        if not response.data:
            return {
                "messages_limit": 0,
                "messages_used": 0,
                "messages_left": 0
            }
        
        user = response.data[0]
        messages_limit = user.get('messages_limit', 0)
        messages_used = user.get('messages_used', 0)
        messages_left = max(0, messages_limit - messages_used)
        
        return {
            "messages_limit": messages_limit,
            "messages_used": messages_used,
            "messages_left": messages_left
        }
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu statusu wiadomości: {e}")
        return {
            "messages_limit": 0,
            "messages_used": 0,
            "messages_left": 0
        }

# Funkcje obsługi konwersacji
def create_new_conversation(user_id):
    """Tworzy nową konwersację dla użytkownika"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        conversation_data = {
            'user_id': user_id,
            'created_at': now,
            'last_message_at': now
        }
        
        response = supabase.table('conversations').insert(conversation_data).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu nowej konwersacji: {e}")
        return None

def get_active_conversation(user_id):
    """Pobiera aktywną konwersację użytkownika (ostatnią)"""
    try:
        response = supabase.table('conversations').select('*').eq('user_id', user_id).order('last_message_at', desc=True).limit(1).execute()
        
        if response.data:
            return response.data[0]
        
        # Jeśli nie ma żadnej konwersacji, utwórz nową
        return create_new_conversation(user_id)
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu aktywnej konwersacji: {e}")
        return create_new_conversation(user_id)

def save_message(conversation_id, user_id, content, is_from_user, model_used=None):
    """Zapisuje wiadomość w bazie danych"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        # Zapisz wiadomość
        message_data = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'content': content,
            'is_from_user': is_from_user,
            'model_used': model_used,
            'created_at': now
        }
        
        message_response = supabase.table('messages').insert(message_data).execute()
        
        # Aktualizuj czas ostatniej wiadomości w konwersacji
        supabase.table('conversations').update({
            'last_message_at': now
        }).eq('id', conversation_id).execute()
        
        if message_response.data:
            return message_response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy zapisywaniu wiadomości: {e}")
        return None

def get_conversation_history(conversation_id, limit=20):
    """Pobiera historię konwersacji"""
    try:
        response = supabase.table('messages').select('*').eq('conversation_id', conversation_id).order('created_at', desc=False) .limit(limit).execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu historii konwersacji: {e}")
        return []

# Funkcje obsługi szablonów promptów
def save_prompt_template(name, description, prompt_text):
    """Zapisuje szablon prompta w bazie danych"""
    try:
        template_data = {
            'name': name,
            'description': description,
            'prompt_text': prompt_text,
            'is_active': True,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat()
        }
        
        response = supabase.table('prompt_templates').insert(template_data).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy zapisywaniu szablonu prompta: {e}")
        return None

def get_prompt_templates():
    """Pobiera wszystkie aktywne szablony promptów"""
    try:
        response = supabase.table('prompt_templates').select('*').eq('is_active', True).execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu szablonów promptów: {e}")
        return []

def get_prompt_template_by_id(template_id):
    """Pobiera szablon prompta po ID"""
    try:
        response = supabase.table('prompt_templates').select('*').eq('id', template_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu szablonu prompta: {e}")
        return None

# Funkcje obsługi tematów konwersacji
def create_conversation_theme(user_id, theme_name):
    """Tworzy nowy temat konwersacji"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        theme_data = {
            'user_id': user_id,
            'theme_name': theme_name,
            'created_at': now,
            'last_used_at': now
        }
        
        response = supabase.table('conversation_themes').insert(theme_data).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu tematu konwersacji: {e}")
        return None

def get_user_themes(user_id):
    """Pobiera listę tematów konwersacji użytkownika"""
    try:
        response = supabase.table('conversation_themes').select('*').eq('user_id', user_id).eq('is_active', True).order('last_used_at', desc=True).execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu tematów konwersacji: {e}")
        return []

def get_theme_by_id(theme_id):
    """Pobiera temat konwersacji po ID"""
    try:
        response = supabase.table('conversation_themes').select('*').eq('id', theme_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu tematu konwersacji: {e}")
        return None

def create_themed_conversation(user_id, theme_id):
    """Tworzy nową konwersację dla określonego tematu"""
    try:
        now = datetime.datetime.now(pytz.UTC).isoformat()
        
        conversation_data = {
            'user_id': user_id,
            'created_at': now,
            'last_message_at': now,
            'theme_id': theme_id
        }
        
        conversation_response = supabase.table('conversations').insert(conversation_data).execute()
        
        # Aktualizuj czas ostatniego użycia tematu
        supabase.table('conversation_themes').update({
            'last_used_at': now
        }).eq('id', theme_id).execute()
        
        if conversation_response.data:
            return conversation_response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu konwersacji dla tematu: {e}")
        return None

def get_active_themed_conversation(user_id, theme_id):
    """Pobiera aktywną konwersację dla określonego tematu"""
    try:
        response = supabase.table('conversations').select('*').eq('user_id', user_id).eq('theme_id', theme_id).order('last_message_at', desc=True).limit(1).execute()
        
        if response.data:
            return response.data[0]
        
        # Jeśli nie znaleziono konwersacji dla tego tematu, utwórz nową
        return create_themed_conversation(user_id, theme_id)
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu aktywnej konwersacji dla tematu: {e}")
        return create_themed_conversation(user_id, theme_id)

# Funkcje obsługi kodów aktywacyjnych
def create_activation_code(credits):
    """Tworzy nowy kod aktywacyjny"""
    try:
        from random import choice
        import string
        
        # Generuj unikalny kod
        characters = string.ascii_uppercase + string.digits
        code = ''.join(choice(characters) for _ in range(8))
        
        # Zapisz kod w bazie danych
        code_data = {
            'code': code,
            'credits': credits,
            'created_at': datetime.datetime.now(pytz.UTC).isoformat()
        }
        
        response = supabase.table('activation_codes').insert(code_data).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu kodu aktywacyjnego: {e}")
        return None

def use_activation_code(user_id, code):
    """Używa kodu aktywacyjnego"""
    try:
        # Sprawdź, czy kod istnieje i nie został użyty
        response = supabase.table('activation_codes').select('*').eq('code', code).eq('is_used', False).execute()
        
        if not response.data:
            return False, 0
        
        code_data = response.data[0]
        credits = code_data['credits']
        
        # Oznacz kod jako użyty
        now = datetime.datetime.now(pytz.UTC).isoformat()
        supabase.table('activation_codes').update({
            'is_used': True,
            'used_by': user_id,
            'used_at': now
        }).eq('id', code_data['id']).execute()
        
        # Dodaj kredyty użytkownikowi
        add_user_credits(user_id, credits, f"Aktywacja kodu {code}")
        
        return True, credits
    except Exception as e:
        logger.error(f"Błąd przy aktywacji kodu: {e}")
        return False, 0

def get_credit_transactions(user_id, days=30):
    """
    Pobiera historię transakcji kredytowych użytkownika z określonej liczby dni
    
    Args:
        user_id (int): ID użytkownika
        days (int): Liczba dni wstecz
        
    Returns:
        list: Lista transakcji
    """
    try:
        start_date = (datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=days)).isoformat()
        
        response = supabase.table('credit_transactions').select('*')\
            .eq('user_id', user_id)\
            .gte('created_at', start_date)\
            .order('created_at', desc=False).execute()
            
        return response.data
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu transakcji kredytowych: {e}")
        return []

def get_credit_usage_by_type(user_id, days=30):
    """
    Pobiera sumaryczne zużycie kredytów według typu transakcji
    
    Args:
        user_id (int): ID użytkownika
        days (int): Liczba dni wstecz
        
    Returns:
        dict: Słownik z sumami zużycia według typów
    """
    try:
        transactions = get_credit_transactions(user_id, days)
        
        # Analiza transakcji po stronie klienta
        usage_breakdown = {}
        for trans in transactions:
            if trans['transaction_type'] != 'deduct':
                continue
                
            description = trans.get('description', 'Inne')
            category = "Inne"
            
            if "Wiadomość" in description:
                category = "Wiadomości"
            elif "obraz" in description or "DALL-E" in description:
                category = "Obrazy"
            elif "dokument" in description:
                category = "Analiza dokumentów"
            elif "zdjęci" in description or "zdjęc" in description:
                category = "Analiza zdjęć"
            
            if category not in usage_breakdown:
                usage_breakdown[category] = 0
            usage_breakdown[category] += trans['amount']
            
        return usage_breakdown
    except Exception as e:
        logger.error(f"Błąd przy analizie zużycia kredytów: {e}")
        return {}

def get_user_language(user_id):
    """Pobiera język użytkownika"""
    try:
        response = supabase.table('users').select('language, language_code').eq('id', user_id).execute()
        
        if response.data:
            user_data = response.data[0]
            language = user_data.get('language')
            
            # Jeśli nie ma language, użyj language_code
            if not language:
                language = user_data.get('language_code')
            
            return language or "pl"
    except Exception as e:
        logger.error(f"Błąd przy pobieraniu języka użytkownika: {e}")
        return "pl"