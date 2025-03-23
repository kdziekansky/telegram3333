from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import BOT_NAME, AVAILABLE_LANGUAGES
from utils.translations import get_text
from database.supabase_client import get_or_create_user, update_user_language
from utils.user_utils import get_user_language
from utils.menu_manager import update_menu_message, store_menu_state

# Zabezpieczony import z awaryjnym fallbackiem
try:
    from utils.referral import use_referral_code
except ImportError:
    # Fallback jeśli import nie zadziała
    def use_referral_code(user_id, code):
        """
        Prosta implementacja awaryjnego fallbacku dla use_referral_code
        """
        # Jeśli kod ma format REF123, wyodrębnij ID polecającego
        if code.startswith("REF") and code[3:].isdigit():
            referrer_id = int(code[3:])
            # Sprawdź, czy użytkownik nie używa własnego kodu
            if referrer_id == user_id:
                return False, None
            # Dodanie kredytów zostałoby implementowane tutaj w prawdziwym przypadku
            return True, referrer_id
        return False, None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługa komendy /start
    Wyświetla od razu menu powitalne dla istniejących użytkowników,
    a wybór języka tylko dla nowych
    """
    try:
        user = update.effective_user
        user_id = user.id
        
        # Sprawdź, czy użytkownik istnieje w bazie
        user_data = get_or_create_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )
        
        # Sprawdź, czy język jest już ustawiony
        language = get_user_language(context, user_id)
        
        # Sprawdź czy to domyślny język (pl) czy wybrany przez użytkownika
        has_language_in_context = ('user_data' in context.chat_data and 
                                  user_id in context.chat_data['user_data'] and 
                                  'language' in context.chat_data['user_data'][user_id])
        
        # Sprawdź też w bazie danych, czy użytkownik ma już ustawiony język
        has_language_in_db = False
        try:
            from database.supabase_client import supabase
            response = supabase.table('users').select('language').eq('id', user_id).execute()
            if response.data and response.data[0].get('language'):
                has_language_in_db = True
        except Exception:
            pass  # Ignoruj błędy przy sprawdzaniu bazy

        # Jeśli użytkownik ma już ustawiony język, pokaż menu od razu
        if has_language_in_context or has_language_in_db:
            await show_welcome_message(update, context, user_id=user_id, language=language)
        else:
            # Jeśli to nowy użytkownik - pokaż wybór języka
            await show_language_selection(update, context)
        
    except Exception as e:
        print(f"Błąd w funkcji start_command: {e}")
        import traceback
        traceback.print_exc()
        
        language = "pl"  # Domyślny język w przypadku błędu
        await update.message.reply_text(
            get_text("initialization_error", language, default="Wystąpił błąd podczas inicjalizacji bota. Spróbuj ponownie później.")
        )

async def show_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None, language=None):
    """
    Wyświetla wiadomość powitalną z menu jako zdjęcie z podpisem
    """
    try:
        if not user_id:
            user_id = update.effective_user.id
            
        if not language:
            language = get_user_language(context, user_id)
            if not language:
                language = "pl"  # Domyślny język
        
        # Zapisz język w kontekście
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['language'] = language
        
        # Pobierz stan kredytów
        from database.credits_client import get_user_credits
        credits = get_user_credits(user_id)
        
        # Link do zdjęcia bannera
        banner_url = "https://i.imgur.com/YPubLDE.png?v-1123"
        
        # Pobierz przetłumaczony tekst powitalny
        welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
        
        # Utwórz klawiaturę menu
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
        
        # Wyślij zdjęcie z podpisem i menu
        message = await update.message.reply_photo(
            photo=banner_url,
            caption=welcome_text,
            reply_markup=reply_markup
        )
        
        # Zapisz ID wiadomości menu i stan menu
        store_menu_state(context, user_id, 'main', message.message_id)
        
        return message
    except Exception as e:
        print(f"Błąd w funkcji show_welcome_message: {e}")
        # Fallback do tekstu w przypadku błędu
        await update.message.reply_text(
            "Wystąpił błąd podczas wyświetlania wiadomości powitalnej. Spróbuj ponownie później."
        )
        return None