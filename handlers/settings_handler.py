# handlers/settings_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import AVAILABLE_LANGUAGES, AVAILABLE_MODELS, CREDIT_COSTS
from utils.translations import get_text
from utils.user_utils import get_user_language, mark_chat_initialized
from utils.menu_manager import update_menu_message, store_menu_state
from database.supabase_client import update_user_language

async def handle_settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje callbacki związane z ustawieniami"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Obsługa opcji ustawień
    if query.data == "settings_model":
        await handle_model_settings(update, context)
        return True
    elif query.data == "settings_language":
        await handle_language_settings(update, context)
        return True
    elif query.data == "settings_name":
        await handle_name_settings(update, context)
        return True
    
    return False  # Nie obsłużono callbacku

async def handle_model_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje ustawienia modelu AI z ulepszonym UI"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    print(f"Obsługa wyboru modelu dla użytkownika {user_id}")
    
    # Tworzymy klawiaturę z dostępnymi modelami
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Dodaj informację o koszcie kredytów
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{model_name} ({credit_cost} kredytów/wiadomość)", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Wyślij nową wiadomość zamiast edytować
    message_text = get_text("settings_choose_model", language)
    result = await update_menu_message(
        query, 
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'model_selection')
    
    return result

async def handle_language_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje ustawienia języka"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Przygotuj klawiaturę z dostępnymi językami
    keyboard = []
    for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
        keyboard.append([
            InlineKeyboardButton(
                lang_name, 
                callback_data=f"start_lang_{lang_code}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Wyślij wiadomość z wyborem języka
    message_text = get_text("settings_choose_language", language, default="Wybierz język:")
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'language_selection')
    
    return result

async def handle_name_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje ustawienia nazwy użytkownika"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = get_text("settings_change_name", language, default="Aby zmienić swoją nazwę, użyj komendy /setname [twoja_nazwa].\n\nNa przykład: /setname Jan Kowalski")
    keyboard = [[InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'name_settings')
    
    return result