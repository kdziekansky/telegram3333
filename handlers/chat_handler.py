from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import DEFAULT_MODEL, MAX_CONTEXT_MESSAGES, AVAILABLE_MODELS, CHAT_MODES
from database.supabase_client import (
    check_active_subscription, get_active_conversation, 
    save_message, get_conversation_history, check_message_limit,
    increment_messages_used, get_message_status
)
from utils.openai_client import chat_completion_stream, prepare_messages_from_history
from utils.translations import get_text
from utils.user_utils import get_user_language, is_chat_initialized, mark_chat_initialized
from handlers.menu_handler import get_user_language
import asyncio

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika ze strumieniowaniem odpowiedzi"""
    user_id = update.effective_user.id
    user_message = update.message.text
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik zainicjował czat
    from utils.user_utils import is_chat_initialized
    if not is_chat_initialized(context, user_id):
        keyboard = [
            [InlineKeyboardButton(get_text("start_new_chat", language, default="Rozpocznij nowy czat"), callback_data="quick_new_chat")],
            [InlineKeyboardButton(get_text("select_mode", language, default="Wybierz tryb czatu"), callback_data="menu_section_chat_modes")],
            [InlineKeyboardButton(get_text("menu_help", language, default="Pomoc"), callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_text("no_active_chat_message", language, default="Aby rozpocząć używanie AI, najpierw utwórz nowy czat używając /newchat lub przycisku poniżej. Możesz również wybrać tryb czatu z menu."),
            reply_markup=reply_markup
        )
        return
    
    print(f"Otrzymano wiadomość od użytkownika {user_id}: {user_message}")
    
    # Określ tryb i koszt kredytów
    current_mode = "no_mode"
    credit_cost = 1
    
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            current_mode = user_data['current_mode']
            credit_cost = CHAT_MODES[current_mode]["credit_cost"]
    
    print(f"Tryb: {current_mode}, koszt kredytów: {credit_cost}")
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    has_credits = check_user_credits(user_id, credit_cost)
    print(f"Czy użytkownik ma wystarczająco kredytów: {has_credits}")
    
    if not has_credits:
        keyboard = [
            [InlineKeyboardButton(get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="menu_credits_buy")],
            [InlineKeyboardButton(get_text("menu_back_main", language, default="Menu główne"), callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_text("subscription_expired", language),
            reply_markup=reply_markup
        )
        return
    
    # Pobierz lub utwórz aktywną konwersację
    try:
        conversation = get_active_conversation(user_id)
        conversation_id = conversation['id']
        print(f"Aktywna konwersacja: {conversation_id}")
    except Exception as e:
        print(f"Błąd przy pobieraniu konwersacji: {e}")
        await update.message.reply_text(get_text("conversation_error", language))
        return
    
    # Zapisz wiadomość użytkownika do bazy danych
    try:
        save_message(conversation_id, user_id, user_message, is_from_user=True)
        print("Wiadomość użytkownika zapisana w bazie")
    except Exception as e:
        print(f"Błąd przy zapisie wiadomości użytkownika: {e}")
    
    # Wyślij informację, że bot pisze
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Pobierz historię konwersacji
    try:
        history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
        print(f"Pobrano historię konwersacji, liczba wiadomości: {len(history)}")
    except Exception as e:
        print(f"Błąd przy pobieraniu historii: {e}")
        history = []
    
    # Określ model do użycia - domyślny lub z trybu czatu
    model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
    
    # Jeśli użytkownik wybrał konkretny model, użyj go
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data:
            model_to_use = user_data['current_model']
            # Aktualizuj koszt kredytów na podstawie modelu
            credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
    
    print(f"Używany model: {model_to_use}")
    
    # Przygotuj system prompt z wybranego trybu
    system_prompt = CHAT_MODES[current_mode]["prompt"]
    
    # Przygotuj wiadomości dla API OpenAI
    messages = prepare_messages_from_history(history, user_message, system_prompt)
    print(f"Przygotowano {len(messages)} wiadomości dla API")
    
    # Wyślij początkową pustą wiadomość, którą będziemy aktualizować
    response_message = await update.message.reply_text(get_text("generating_response", language))
    
    # Zainicjuj pełną odpowiedź
    full_response = ""
    buffer = ""
    last_update = datetime.datetime.now().timestamp()
    
    # Spróbuj wygenerować odpowiedź
    try:
        print("Rozpoczynam generowanie odpowiedzi strumieniowej...")
        # Generuj odpowiedź strumieniowo
        async for chunk in chat_completion_stream(messages, model=model_to_use):
            full_response += chunk
            buffer += chunk
            
            # Aktualizuj wiadomość co 1 sekundę lub gdy bufor jest wystarczająco duży
            current_time = datetime.datetime.now().timestamp()
            if current_time - last_update >= 1.0 or len(buffer) > 100:
                try:
                    # Dodaj migający kursor na końcu wiadomości
                    await response_message.edit_text(full_response + "▌", parse_mode=ParseMode.MARKDOWN)
                    buffer = ""
                    last_update = current_time
                except Exception as e:
                    # Jeśli wystąpi błąd (np. wiadomość nie została zmieniona), kontynuuj
                    print(f"Błąd przy aktualizacji wiadomości: {e}")
        
        print("Zakończono generowanie odpowiedzi")
        
        # Aktualizuj wiadomość z pełną odpowiedzią bez kursora
        try:
            await response_message.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            # Jeśli wystąpi błąd formatowania Markdown, wyślij bez formatowania
            print(f"Błąd formatowania Markdown: {e}")
            await response_message.edit_text(full_response)
        
        # Zapisz odpowiedź do bazy danych
        save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
        
        # Odejmij kredyty
        deduct_user_credits(user_id, credit_cost, get_text("message_model", language, model=model_to_use, default=f"Wiadomość ({model_to_use})"))
        print(f"Odjęto {credit_cost} kredytów za wiadomość")
    except Exception as e:
        print(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
        await response_message.edit_text(get_text("response_error", language, error=str(e)))
        return
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        # Dodaj przycisk doładowania kredytów
        keyboard = [[InlineKeyboardButton(get_text("buy_credits_btn_with_icon", language, default="🛒 Kup kredyty"), callback_data="menu_credits_buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Zwiększ licznik wykorzystanych wiadomości
    increment_messages_used(user_id)