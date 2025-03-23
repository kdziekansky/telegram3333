from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CHAT_MODES, DEFAULT_MODEL, MAX_CONTEXT_MESSAGES, CREDIT_COSTS
from utils.translations import get_text
from utils.user_utils import get_user_language, is_chat_initialized, mark_chat_initialized
from database.supabase_client import (
    get_active_conversation, save_message, get_conversation_history, increment_messages_used
)
from database.credits_client import get_user_credits, check_user_credits, deduct_user_credits
from utils.openai_client import chat_completion_stream, prepare_messages_from_history
from utils.visual_styles import create_header, create_status_indicator
from utils.credit_warnings import check_operation_cost, format_credit_usage_report
from utils.tips import get_contextual_tip, get_random_tip, should_show_tip
import datetime

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa wiadomości tekstowych od użytkownika ze strumieniowaniem odpowiedzi i ulepszonym formatowaniem"""
    user_id = update.effective_user.id
    user_message = update.message.text
    language = get_user_language(context, user_id)
    
    print(f"Otrzymano wiadomość od użytkownika {user_id}: {user_message}")
    
    # Sprawdź, czy użytkownik zainicjował czat
    if not is_chat_initialized(context, user_id):
        # Enhanced UI for chat initialization prompt
        message = create_header("Rozpocznij nowy czat", "chat")
        message += (
            "Aby rozpocząć używanie AI, najpierw utwórz nowy czat używając /newchat "
            "lub przycisku poniżej. Możesz również wybrać tryb czatu z menu."
        )
        
        keyboard = [
            [InlineKeyboardButton("🆕 " + get_text("start_new_chat", language, default="Rozpocznij nowy czat"), callback_data="quick_new_chat")],
            [InlineKeyboardButton("📋 " + get_text("select_mode", language, default="Wybierz tryb czatu"), callback_data="menu_section_chat_modes")],
            [InlineKeyboardButton("❓ " + get_text("menu_help", language, default="Pomoc"), callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Określ tryb i koszt kredytów
    current_mode = "no_mode"
    credit_cost = 1
    
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            current_mode = user_data['current_mode']
            credit_cost = CHAT_MODES[current_mode]["credit_cost"]
    
    print(f"Tryb: {current_mode}, koszt kredytów: {credit_cost}")
    
    # Get current credits
    credits = get_user_credits(user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    if not check_user_credits(user_id, credit_cost):
        # Enhanced credit warning with visual indicators
        warning_message = create_header("Niewystarczające kredyty", "warning")
        warning_message += (
            f"Nie masz wystarczającej liczby kredytów, aby wysłać wiadomość.\n\n"
            f"▪️ Koszt operacji: *{credit_cost}* kredytów\n"
            f"▪️ Twój stan kredytów: *{credits}* kredytów\n\n"
            f"Potrzebujesz jeszcze *{credit_cost - credits}* kredytów."
        )
        
        # Add credit recommendation if available
        from utils.credit_warnings import get_credit_recommendation
        recommendation = get_credit_recommendation(user_id, context)
        if recommendation:
            from utils.visual_styles import create_section
            warning_message += "\n\n" + create_section("Rekomendowany pakiet", 
                f"▪️ {recommendation['package_name']} - {recommendation['credits']} kredytów\n"
                f"▪️ Cena: {recommendation['price']} PLN\n"
                f"▪️ {recommendation['reason']}")
        
        keyboard = [
            [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ " + get_text("menu_back_main", language, default="Menu główne"), callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            warning_message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check operation cost and show warning if needed
    cost_warning = check_operation_cost(user_id, credit_cost, credits, "Wiadomość AI", context)
    if cost_warning['require_confirmation'] and cost_warning['level'] in ['warning', 'critical']:
        # Show warning and ask for confirmation
        warning_message = create_header("Potwierdzenie kosztu", "warning")
        warning_message += cost_warning['message'] + "\n\nCzy chcesz kontynuować?"
        
        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Tak, wyślij", callback_data=f"confirm_message"),
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store message in context for later use
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
            
        context.chat_data['user_data'][user_id]['pending_message'] = user_message
        
        await update.message.reply_text(
            warning_message,
            parse_mode=ParseMode.MARKDOWN,
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