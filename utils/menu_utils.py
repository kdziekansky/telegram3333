# utils/menu_utils.py
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.translations import get_text


logger = logging.getLogger(__name__)

async def update_menu(query, text, keyboard, parse_mode=None):
    """
    Ulepszona funkcja do aktualizacji wiadomości menu
    
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
            # Zapisz ID czatu, bo będziemy usuwać wiadomość
            chat_id = query.message.chat_id
            
            # Wyślij nową wiadomość
            await query.bot.send_message(
                chat_id=chat_id,
                text=text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", ""),
                reply_markup=keyboard
            )
            return True
        except Exception as e3:
            logger.error(f"Cannot send new message: {e3}")
            return False

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

def create_menu_buttons(button_configs, language):
    """
    Tworzy przyciski menu na podstawie konfiguracji
    
    Args:
        button_configs (list): Lista konfiguracji przycisków
        language (str): Kod języka
    
    Returns:
        InlineKeyboardMarkup: Klawiatura z przyciskami
    """
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

# Stwórz globalną instancję
menu_state = MenuState()