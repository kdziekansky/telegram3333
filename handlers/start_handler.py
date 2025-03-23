from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import BOT_NAME, AVAILABLE_LANGUAGES
from utils.translations import get_text
from database.supabase_client import get_or_create_user, get_message_status
from database.credits_client import get_user_credits
from utils.user_utils import get_user_language
from utils.menu_utils import update_menu

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
            from database.supabase_client import update_user_language
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
        
        # Użyj centralnej implementacji update_menu
        from utils.menu_utils import update_menu
        try:
            # Bezpośrednio aktualizujemy wiadomość, aby uniknąć problemów z update_menu
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
                
            # Zapisz stan menu poprawnie - używamy bezpośrednio menu_state
            from utils.menu_utils import menu_state
            menu_state.set_state(user_id, 'main')
            menu_state.set_message_id(user_id, query.message.message_id)
            menu_state.save_to_context(context, user_id)
            
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
                from utils.menu_utils import menu_state
                menu_state.set_state(user_id, 'main')
                menu_state.set_message_id(user_id, message.message_id)
                menu_state.save_to_context(context, user_id)
                
                print(f"Wysłano nową wiadomość menu dla użytkownika {user_id}")
            except Exception as e2:
                print(f"Błąd przy wysyłaniu nowej wiadomości: {e2}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"Błąd w funkcji handle_language_selection: {e}")
        import traceback
        traceback.print_exc()

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
        from handlers.menu_handler import store_menu_state
        store_menu_state(context, user_id, 'main', message.message_id)
        
        return message
    except Exception as e:
        print(f"Błąd w funkcji show_welcome_message: {e}")
        # Fallback do tekstu w przypadku błędu
        await update.message.reply_text(
            "Wystąpił błąd podczas wyświetlania wiadomości powitalnej. Spróbuj ponownie później."
        )
        return None