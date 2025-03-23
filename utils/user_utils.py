# utils/user_utils.py
from database.supabase_client import supabase

def get_user_language(context, user_id):
    """
    Pobiera język użytkownika z kontekstu lub bazy danych
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        str: Kod języka (pl, en, ru)
    """
    # Sprawdź, czy język jest zapisany w kontekście
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data'] and 'language' in context.chat_data['user_data'][user_id]:
        return context.chat_data['user_data'][user_id]['language']
    
    # Jeśli nie, pobierz z bazy danych
    try:
        response = supabase.table('users').select('language, language_code').eq('id', user_id).execute()
        
        if response.data:
            user_data = response.data[0]
            
            # Najpierw sprawdź pole language
            if user_data.get('language'):
                language = user_data.get('language')
                
                # Zapisz w kontekście na przyszłość
                if 'user_data' not in context.chat_data:
                    context.chat_data['user_data'] = {}
                
                if user_id not in context.chat_data['user_data']:
                    context.chat_data['user_data'][user_id] = {}
                
                context.chat_data['user_data'][user_id]['language'] = language
                return language
                
            # Jeśli language nie znaleziono, sprawdź language_code
            if user_data.get('language_code'):
                language_code = user_data.get('language_code')
                
                # Zapisz w kontekście na przyszłość
                if 'user_data' not in context.chat_data:
                    context.chat_data['user_data'] = {}
                
                if user_id not in context.chat_data['user_data']:
                    context.chat_data['user_data'][user_id] = {}
                
                context.chat_data['user_data'][user_id]['language'] = language_code
                return language_code
    except Exception as e:
        print(f"Błąd pobierania języka z bazy: {e}")
    
    # Domyślny język, jeśli wszystkie metody zawiodły
    return "pl"

def mark_chat_initialized(context, user_id):
    """
    Oznacza czat jako zainicjowany przez użytkownika.
    Ta funkcja powinna być wywoływana przy każdym jawnym rozpoczęciu czatu:
    - Po wykonaniu /newchat
    - Po wyborze trybu czatu
    - Po wyborze modelu
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
    """
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    # Ustaw flagę inicjalizacji
    context.chat_data['user_data'][user_id]['chat_initialized'] = True
    print(f"Czat został oznaczony jako zainicjowany dla użytkownika {user_id}")

def is_chat_initialized(context, user_id):
    """
    Sprawdza, czy czat został zainicjowany przez użytkownika.
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        bool: True jeśli czat został zainicjowany, False w przeciwnym razie
    """
    # Sprawdź bezpośrednio flagę inicjalizacji
    if ('user_data' in context.chat_data and 
        user_id in context.chat_data['user_data'] and 
        context.chat_data['user_data'][user_id].get('chat_initialized', False)):
        return True
    
    # Sprawdź, czy użytkownik ma ustawiony tryb lub model w kontekście
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data or 'current_model' in user_data:
            # Automatycznie oznacz jako zainicjowany, jeśli ma tryb lub model
            mark_chat_initialized(context, user_id)
            return True
    
    return False