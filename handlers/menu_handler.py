# handlers/menu_handler.py
"""
Centralny moduł do obsługi systemu menu bota - po refaktoryzacji
Służy głównie jako router callbacków do odpowiednich handlerów
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES, AVAILABLE_MODELS, DEFAULT_MODEL
from utils.translations import get_text
from utils.user_utils import get_user_language
from utils.menu_manager import update_menu_message, store_menu_state, get_navigation_path
from utils.visual_styles import create_header, create_section
from handlers.model_handler import handle_model_selection
from handlers.language_handler import handle_language_selection
from handlers.settings_handler import handle_settings_callbacks
from handlers.menu_sections import handle_chat_modes_section, handle_credits_section, handle_settings_section, handle_history_section, handle_help_section, handle_image_section
from handlers.menu_navigation import handle_back_to_main


# ==================== FUNKCJE POMOCNICZE DO ZARZĄDZANIA DANYMI UŻYTKOWNIKA ====================

def get_user_current_mode(context, user_id):
    """Pobiera aktualny tryb czatu użytkownika"""
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            return user_data['current_mode']
    return "no_mode"

def get_user_current_model(context, user_id):
    """Pobiera aktualny model AI użytkownika"""
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data and user_data['current_model'] in AVAILABLE_MODELS:
            return user_data['current_model']
    return DEFAULT_MODEL  # Domyślny model

# ==================== GŁÓWNA FUNKCJA OBSŁUGI MENU ====================

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Centralny router do obsługi wszystkich callbacków związanych z menu
    
    Args:
        update: Obiekt aktualizacji Telegram
        context: Kontekst bota
        
    Returns:
        bool: True jeśli callback został obsłużony, False w przeciwnym razie
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Najpierw odpowiedz, aby usunąć oczekiwanie
    await query.answer()
    
    # Dodajmy logging dla debugowania
    print(f"Menu callback received: {query.data}")
    
    # Obsługa sekcji menu
    if query.data == "menu_section_chat_modes":
        from handlers.menu_sections import handle_chat_modes_section
        nav_path = get_navigation_path('chat_modes', language)
        return await handle_chat_modes_section(update, context, nav_path)
    elif query.data == "menu_section_credits":
        from handlers.menu_sections import handle_credits_section
        nav_path = get_navigation_path('credits', language)
        return await handle_credits_section(update, context, nav_path)
    elif query.data == "menu_section_history":
        from handlers.menu_sections import handle_history_section
        nav_path = get_navigation_path('history', language)
        return await handle_history_section(update, context, nav_path)
    elif query.data == "menu_section_settings":
        from handlers.menu_sections import handle_settings_section
        nav_path = get_navigation_path('settings', language)
        return await handle_settings_section(update, context, nav_path)
    elif query.data == "menu_help":
        from handlers.menu_sections import handle_help_section
        nav_path = get_navigation_path('help', language)
        return await handle_help_section(update, context, nav_path)
    elif query.data == "menu_image_generate":
        from handlers.menu_sections import handle_image_section
        nav_path = get_navigation_path('image', language)
        return await handle_image_section(update, context, nav_path)
    elif query.data == "menu_back_main":
        from handlers.menu_navigation import handle_back_to_main
        return await handle_back_to_main(update, context)
        
    # Obsługa opcji menu kredytów
    if query.data.startswith("menu_credits_") or query.data.startswith("credits_") or query.data == "Kup":
        from handlers.credit_handler import handle_credit_callback
        return await handle_credit_callback(update, context)
    
    # Obsługa opcji menu płatności
    if query.data.startswith("payment_") or query.data.startswith("buy_package_"):
        from handlers.payment_handler import handle_payment_callback
        return await handle_payment_callback(update, context)
    
    # Obsługa opcji menu historii
    if query.data.startswith("history_"):
        from handlers.menu_sections import handle_history_callbacks
        return await handle_history_callbacks(update, context)
    
    # Obsługa opcji menu ustawień i języka
    if query.data.startswith("settings_"):
        from handlers.settings_handler import handle_settings_callbacks
        return await handle_settings_callbacks(update, context)
    elif query.data.startswith("start_lang_"):
        from handlers.language_handler import handle_language_selection
        return await handle_language_selection(update, context)
    
    # Obsługa wyboru modelu
    if query.data.startswith("model_"):
        from handlers.model_handler import handle_model_selection
        model_id = query.data.replace("model_", "")
        return await handle_model_selection(update, context, model_id)
        
    # Obsługa wyboru trybu
    if query.data.startswith("mode_"):
        from handlers.mode_handler import handle_mode_selection
        mode_id = query.data.replace("mode_", "")
        return await handle_mode_selection(update, context, mode_id)
    
    # Obsługa szybkich akcji
    if query.data.startswith("quick_"):
        from handlers.callback_handler import handle_callback_query
        return await handle_callback_query(update, context)
    
    # Obsługa onboardingu
    if query.data.startswith("onboarding_"):
        from handlers.onboarding_handler import handle_onboarding_callback
        return await handle_onboarding_callback(update, context)
    
    # Obsługa potwierdzeń operacji
    if query.data.startswith("confirm_"):
        if query.data.startswith("confirm_image_"):
            from handlers.confirmation_handler import handle_image_confirmation
            return await handle_image_confirmation(update, context)
        elif query.data.startswith("confirm_doc_"):
            from handlers.confirmation_handler import handle_document_confirmation
            return await handle_document_confirmation(update, context)
        elif query.data.startswith("confirm_photo_"):
            from handlers.confirmation_handler import handle_photo_confirmation
            return await handle_photo_confirmation(update, context)
        elif query.data == "confirm_message" or query.data == "cancel_operation":
            from handlers.confirmation_handler import handle_message_confirmation
            return await handle_message_confirmation(update, context)
    
    # Obsługa nieznanych callbacków
    from handlers.callback_handler import handle_unknown_callback
    return await handle_unknown_callback(update, context)

# ==================== FUNKCJE KOMEND ====================

async def set_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ustawia nazwę użytkownika
    Użycie: /setname [nazwa]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy podano argumenty
    if not context.args or len(' '.join(context.args)) < 1:
        await update.message.reply_text(
            get_text("settings_change_name", language),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Połącz argumenty, aby utworzyć nazwę
    new_name = ' '.join(context.args)
    
    # Ogranicz długość nazwy
    if len(new_name) > 50:
        new_name = new_name[:47] + "..."
    
    try:
        # Aktualizuj nazwę użytkownika w bazie danych Supabase
        from database.supabase_client import supabase
        
        response = supabase.table('users').update(
            {"first_name": new_name}
        ).eq('id', user_id).execute()
        
        # Aktualizuj nazwę w kontekście, jeśli istnieje
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['name'] = new_name
        
        # Potwierdź zmianę nazwy
        await update.message.reply_text(
            f"{get_text('name_changed', language)} *{new_name}*",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Błąd przy zmianie nazwy użytkownika: {e}")
        await update.message.reply_text(
            "Wystąpił błąd podczas zmiany nazwy. Spróbuj ponownie później.",
            parse_mode=ParseMode.MARKDOWN
        )