from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.translations import get_text
from utils.user_utils import get_user_language
from utils.menu_manager import update_menu_message, store_menu_state
from database.supabase_client import update_user_language
from config import AVAILABLE_LANGUAGES

# Przenieś tu funkcje związane z wyborem języka:
async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje wybór języka przez użytkownika
    """
    try:
        query = update.callback_query
        await query.answer()
        
        if not query.data.startswith("start_lang_"):
            return
        
        language = query.data[11:]  # Usuń prefix "start_lang_"
        user_id = query.from_user.id
        
        # Zapisz język w bazie danych
        try:
            update_user_language(user_id, language)
        except Exception as e:
            print(f"Błąd zapisywania języka: {e}")
        
        # Zapisz język w kontekście
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['language'] = language
        
        # Pobierz przetłumaczony tekst powitalny
        welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
        
        # Utwórz klawiaturę menu z przetłumaczonymi tekstami
        keyboard = [
            [
                InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
                InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
            ],
            [
                InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
                InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
            ],
            [
                InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
                InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Bezpośrednio aktualizujemy wiadomość, aby uniknąć problemów
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=welcome_text,
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    text=welcome_text,
                    reply_markup=reply_markup
                )
                
            # Zapisz stan menu
            store_menu_state(context, user_id, 'main', query.message.message_id)
            
            print(f"Menu główne wyświetlone poprawnie dla użytkownika {user_id}")
        except Exception as e:
            print(f"Błąd przy aktualizacji wiadomości: {e}")
            # Jeśli nie możemy edytować, to spróbujmy wysłać nową wiadomość
            try:
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup
                )
                
                # Zapisz stan menu
                store_menu_state(context, user_id, 'main', message.message_id)
                
                print(f"Wysłano nową wiadomość menu dla użytkownika {user_id}")
            except Exception as e2:
                print(f"Błąd przy wysyłaniu nowej wiadomości: {e2}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"Błąd w funkcji handle_language_selection: {e}")
        import traceback
        traceback.print_exc()
        
def create_language_selection_markup(language):
    """Tworzy klawiaturę dla wyboru języka"""
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
    
    return InlineKeyboardMarkup(keyboard)

# ==================== FUNKCJE OBSŁUGUJĄCE CALLBACK ====================

async def handle_mode_callbacks(update, context):
    """Obsługuje callbacki związane z trybami czatu"""
    query = update.callback_query
    
    # Obsługa wyboru trybu czatu
    if query.data.startswith("mode_"):
        mode_id = query.data[5:]  # Usuń prefiks "mode_"
        try:
            await handle_mode_selection(update, context, mode_id)
            return True
        except Exception as e:
            print(f"Błąd przy obsłudze wyboru trybu: {e}")
            await query.answer("Wystąpił błąd podczas wyboru trybu czatu.")
            return True
    
    return False  # Nie obsłużono callbacku

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /language
    Wyświetla tylko ekran wyboru języka
    """
    return await show_language_selection(update, context)

async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla wybór języka przy pierwszym uruchomieniu ze zdjęciem
    """
    try:
        # Utwórz przyciski dla każdego języka
        keyboard = []
        for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
            keyboard.append([InlineKeyboardButton(lang_name, callback_data=f"start_lang_{lang_code}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Link do zdjęcia bannera
        banner_url = "https://i.imgur.com/OiPImmC.png?v-111"
        
        # Użyj neutralnego języka dla pierwszej wiadomości
        language_message = f"Wybierz język / Choose language / Выберите язык:"
        
        # Wyślij zdjęcie z tekstem wyboru języka
        await update.message.reply_photo(
            photo=banner_url,
            caption=language_message,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Błąd w funkcji show_language_selection: {e}")
        import traceback
        traceback.print_exc()
        
        await update.message.reply_text(
            "Wystąpił błąd podczas wyboru języka. Spróbuj ponownie później."
        )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje wybór języka przez użytkownika
    """
    try:
        query = update.callback_query
        await query.answer()
        
        if not query.data.startswith("start_lang_"):
            return
        
        language = query.data[11:]  # Usuń prefix "start_lang_"
        user_id = query.from_user.id
        
        # Zapisz język w bazie danych
        try:
            update_user_language(user_id, language)
        except Exception as e:
            print(f"Błąd zapisywania języka: {e}")
        
        # Zapisz język w kontekście
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['language'] = language
        
        # Pobierz przetłumaczony tekst powitalny
        welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
        
        # Utwórz klawiaturę menu z przetłumaczonymi tekstami
        keyboard = [
            [
                InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
                InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
            ],
            [
                InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
                InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
            ],
            [
                InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
                InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Bezpośrednio aktualizujemy wiadomość, aby uniknąć problemów
            if hasattr(query.message, 'caption'):
                await query.edit_message_caption(
                    caption=welcome_text,
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    text=welcome_text,
                    reply_markup=reply_markup
                )
                
            # Zapisz stan menu
            store_menu_state(context, user_id, 'main', query.message.message_id)
            
            print(f"Menu główne wyświetlone poprawnie dla użytkownika {user_id}")
        except Exception as e:
            print(f"Błąd przy aktualizacji wiadomości: {e}")
            # Jeśli nie możemy edytować, to spróbujmy wysłać nową wiadomość
            try:
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup
                )
                
                # Zapisz stan menu
                store_menu_state(context, user_id, 'main', message.message_id)
                
                print(f"Wysłano nową wiadomość menu dla użytkownika {user_id}")
            except Exception as e2:
                print(f"Błąd przy wysyłaniu nowej wiadomości: {e2}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"Błąd w funkcji handle_language_selection: {e}")
        import traceback
        traceback.print_exc()