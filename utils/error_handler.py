# utils/error_handler.py
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.translations import get_text

logger = logging.getLogger(__name__)

async def handle_callback_error(query, error_message, full_error=None, show_retry=True, language=None):
    """
    Ulepszona obsługa błędów podczas przetwarzania callbacków
    
    Args:
        query: Obiekt callback_query
        error_message: Krótka wiadomość o błędzie dla użytkownika
        full_error: Pełny tekst błędu do zalogowania (opcjonalnie)
        show_retry: Czy pokazać przycisk ponowienia próby (opcjonalnie)
        language: Kod języka (opcjonalnie)
    """
    if full_error:
        logger.error(f"Błąd podczas obsługi callbacku: {full_error}")
        import traceback
        traceback.print_exc()
    
    # Próba pobrania języka, jeśli nie został przekazany
    if not language:
        try:
            user_id = query.from_user.id
            # Spróbuj pobrać język z kontekstu
            if hasattr(query, 'bot') and hasattr(query.bot, 'context'):
                context = query.bot.context
                language = get_user_language(context, user_id)
            else:
                # Jeśli nie udało się pobrać języka, użyj domyślnego
                language = "pl"
        except:
            language = "pl"
    
    # Powiadom użytkownika o błędzie przez notyfikację
    try:
        await query.answer(error_message)
    except Exception:
        pass
    
    # Przygotuj klawiaturę z przyciskami
    keyboard = []
    
    # Dodaj przycisk ponowienia próby, jeśli wymagane
    if show_retry:
        keyboard.append([
            InlineKeyboardButton(
                get_text("retry", language, default="Spróbuj ponownie"),
                callback_data=query.data
            )
        ])
    
    # Dodaj pasek szybkiego dostępu
    keyboard.append([
        InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
    ])
    
    # Dodaj przycisk powrotu do menu głównego
    keyboard.append([
        InlineKeyboardButton("⬅️ " + get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Spróbuj zaktualizować wiadomość z informacją o błędzie
    try:
        error_text = f"⚠️ {error_message}\n\n{get_text('error_retry', language, default='Możesz spróbować ponownie lub wrócić do menu głównego.')}"
        
        if hasattr(query.message, 'caption'):
            await query.edit_message_caption(
                caption=error_text,
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(
                text=error_text,
                reply_markup=reply_markup
            )
    except Exception:
        # Jeśli nie udało się zaktualizować wiadomości, spróbuj wysłać nową
        try:
            await query.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⚠️ {error_message}\n\n{get_text('error_retry', language, default='Możesz spróbować ponownie lub wrócić do menu głównego.')}",
                reply_markup=reply_markup
            )
        except Exception:
            # Jeśli i to się nie udało, nie rób nic
            pass

def get_user_language(context, user_id):
    """
    Pomocnicza funkcja do pobierania języka użytkownika
    Importowana dynamicznie, aby uniknąć cyklicznych importów
    
    Args:
        context: Kontekst bota
        user_id: ID użytkownika
        
    Returns:
        str: Kod języka (pl, en, ru)
    """
    try:
        # Importuj funkcję dynamicznie, aby uniknąć cyklicznych importów
        from utils.user_utils import get_user_language as get_lang
        return get_lang(context, user_id)
    except:
        return "pl"  # Domyślny język w przypadku błędu