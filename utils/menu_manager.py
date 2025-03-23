# utils/menu_manager.py
"""
Scentralizowany moduł do zarządzania systemem menu bota
Łączy funkcjonalności z menu_manager.py i menu_utils.py
"""
import logging
from telegram import InlineKeyboardMarkup, ParseMode
from utils.translations import get_text
from utils.user_utils import get_user_language

logger = logging.getLogger(__name__)

class MenuState:
    """Klasa do zarządzania stanem menu"""
    
    def __init__(self):
        self.states = {}  # user_id -> stan menu
        self.message_ids = {}  # user_id -> ID wiadomości menu
    
    def set_state(self, user_id, state):
        """Ustawia stan menu dla użytkownika"""
        self.states[user_id] = state
    
    def get_state(self, user_id, default='main'):
        """Pobiera stan menu dla użytkownika"""
        return self.states.get(user_id, default)
    
    def set_message_id(self, user_id, message_id):
        """Zapisuje ID wiadomości menu dla użytkownika"""
        self.message_ids[user_id] = message_id
    
    def get_message_id(self, user_id):
        """Pobiera ID wiadomości menu dla użytkownika"""
        return self.message_ids.get(user_id)
    
    def save_to_context(self, context, user_id):
        """Zapisuje stan menu do kontekstu"""
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['menu_state'] = self.get_state(user_id)
        if self.get_message_id(user_id):
            context.chat_data['user_data'][user_id]['menu_message_id'] = self.get_message_id(user_id)
    
    def load_from_context(self, context, user_id):
        """Ładuje stan menu z kontekstu"""
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'menu_state' in user_data:
                self.set_state(user_id, user_data['menu_state'])
            if 'menu_message_id' in user_data:
                self.set_message_id(user_id, user_data['menu_message_id'])

# Stwórz globalną instancję do śledzenia stanu menu
menu_state = MenuState()

def store_menu_state(context, user_id, state, message_id=None):
    """
    Zapisuje stan menu dla użytkownika
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        state: Stan menu (np. 'main', 'chat_modes', 'credits', etc.)
        message_id: ID wiadomości z menu (opcjonalnie)
    """
    menu_state.set_state(user_id, state)
    if message_id:
        menu_state.set_message_id(user_id, message_id)
    menu_state.save_to_context(context, user_id)
    logger.debug(f"Zapisano stan menu '{state}' dla użytkownika {user_id}")

def get_menu_state(context, user_id):
    """
    Pobiera stan menu dla użytkownika
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        str: Stan menu
    """
    menu_state.load_from_context(context, user_id)
    return menu_state.get_state(user_id)

def get_menu_message_id(context, user_id):
    """
    Pobiera ID wiadomości menu dla użytkownika
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        int: ID wiadomości menu
    """
    menu_state.load_from_context(context, user_id)
    return menu_state.get_message_id(user_id)

def safe_markdown(text):
    """
    Przygotowuje tekst do bezpiecznego formatowania Markdown
    
    Args:
        text (str): Tekst do zabezpieczenia
    
    Returns:
        str: Zabezpieczony tekst
    """
    if not text:
        return ""
    
    # Upewnij się, że mamy string
    text = str(text)
    
    # Napraw najbardziej problematyczne elementy
    # 1. Upewnij się, że gwiazdki są parzyste
    if text.count('*') % 2 != 0:
        text = text.replace('*', '\\*')
    
    # 2. Upewnij się, że podkreślniki są parzyste
    if text.count('_') % 2 != 0:
        text = text.replace('_', '\\_')
    
    # 3. Upewnij się, że backticki są parzyste
    if text.count('`') % 2 != 0:
        text = text.replace('`', '\\`')
    
    # 4. Unikaj problematycznych sekwencji
    text = text.replace('__', '\\_\\_')
    text = text.replace('**', '\\*\\*')
    
    return text

async def update_menu_message(query, text, keyboard, parse_mode=None):
    """
    Aktualizuje wiadomość menu
    
    Args:
        query: Obiekt callback_query
        text: Tekst do wyświetlenia
        keyboard: Klawiatura z przyciskami
        parse_mode: Tryb formatowania (opcjonalnie)
        
    Returns:
        bool: Czy aktualizacja się powiodła
    """
    try:
        # Sprawdź, czy wiadomość ma caption (zdjęcie) czy jest zwykłym tekstem
        is_caption = hasattr(query.message, 'caption') and query.message.caption is not None
        
        # Próba aktualizacji z formatowaniem
        if is_caption:
            if parse_mode:
                await query.edit_message_caption(
                    caption=text, reply_markup=keyboard, parse_mode=parse_mode
                )
            else:
                await query.edit_message_caption(
                    caption=text, reply_markup=keyboard
                )
        else:
            if parse_mode:
                await query.edit_message_text(
                    text=text, reply_markup=keyboard, parse_mode=parse_mode
                )
            else:
                await query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
        return True
    
    except Exception as e:
        logger.error(f"Menu update error: {e}")
        
        # Jeśli wystąpił błąd formatowania, spróbuj bez formatowania
        if parse_mode:
            try:
                # Usuń znaczniki formatowania
                text = text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
                
                if is_caption:
                    await query.edit_message_caption(
                        caption=text, reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text(
                        text=text, reply_markup=keyboard
                    )
                return True
            except Exception as e2:
                logger.error(f"Second menu update error: {e2}")
        
        # Ostatnia szansa - wyślij nową wiadomość
        try:
            # Wyślij nową wiadomość
            await query.bot.send_message(
                chat_id=query.message.chat_id,
                text=text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", ""),
                reply_markup=keyboard
            )
            return True
        except Exception as e3:
            logger.error(f"Cannot send new message: {e3}")
            return False

async def create_new_menu_message(context, chat_id, text, keyboard, parse_mode=None):
    """
    Tworzy nową wiadomość menu
    
    Args:
        context: Kontekst bota
        chat_id: ID czatu
        text: Tekst do wyświetlenia
        keyboard: Klawiatura z przyciskami
        parse_mode: Tryb formatowania (opcjonalnie)
        
    Returns:
        telegram.Message: Utworzona wiadomość
    """
    try:
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"Błąd przy tworzeniu nowej wiadomości menu: {e}")
        try:
            # Fallback bez formatowania
            return await context.bot.send_message(
                chat_id=chat_id,
                text=text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", ""),
                reply_markup=keyboard
            )
        except Exception as e2:
            logger.error(f"Drugi błąd przy tworzeniu wiadomości menu: {e2}")
            return None

def create_menu_buttons(button_configs, language):
    """
    Tworzy przyciski menu na podstawie konfiguracji
    
    Args:
        button_configs (list): Lista konfiguracji przycisków
        language (str): Kod języka
    
    Returns:
        InlineKeyboardMarkup: Klawiatura z przyciskami
    """
    from telegram import InlineKeyboardButton
    
    keyboard = []
    
    for row_config in button_configs:
        row = []
        for button_config in row_config:
            if isinstance(button_config, tuple) and len(button_config) == 2:
                text_key, callback_data = button_config
                button_text = get_text(text_key, language)
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            elif isinstance(button_config, tuple) and len(button_config) == 3:
                text_key, callback_data, prefix = button_config
                button_text = f"{prefix} {get_text(text_key, language)}"
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            elif isinstance(button_config, dict):
                # Dla przycisków z URL
                text_key = button_config.get('text_key')
                url = button_config.get('url')
                button_text = get_text(text_key, language)
                row.append(InlineKeyboardButton(button_text, url=url))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def get_navigation_path(state, language):
    """
    Generuje tekst paska nawigacyjnego
    
    Args:
        state: Stan menu (np. 'main', 'chat_modes', 'credits', etc.)
        language: Kod języka
        
    Returns:
        str: Tekst paska nawigacyjnego
    """
    # Mapowanie stanów menu na ścieżki nawigacji
    navigation_map = {
        'main': get_text("main_menu", language, default="Menu główne"),
        'chat_modes': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_chat_mode', language, default='Tryb czatu')}",
        'credits': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_credits', language, default='Kredyty')}",
        'settings': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_settings', language, default='Ustawienia')}",
        'history': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_dialog_history', language, default='Historia')}",
        'help': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_help', language, default='Pomoc')}",
        'image': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('image_generate', language, default='Generowanie obrazu')}"
    }
    
    return navigation_map.get(state, get_text("main_menu", language, default="Menu główne"))