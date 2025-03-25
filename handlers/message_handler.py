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
    
    if not is_chat_initialized(context, user_id):
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
    
    current_mode = "no_mode"
    credit_cost = 1
    
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
            current_mode = user_data['current_mode']
            credit_cost = CHAT_MODES[current_mode]["credit_cost"]
    
    credits = get_user_credits(user_id)
    
    if not await check_user_credits(user_id, credit_cost):
        warning_message = create_header("Niewystarczające kredyty", "warning")
        warning_message += (
            f"Nie masz wystarczającej liczby kredytów, aby wysłać wiadomość.\n\n"
            f"▪️ Koszt operacji: *{credit_cost}* kredytów\n"
            f"▪️ Twój stan kredytów: *{credits}* kredytów\n\n"
            f"Potrzebujesz jeszcze *{credit_cost - credits}* kredytów."
        )
        
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
    
    cost_warning = check_operation_cost(user_id, credit_cost, credits, "Wiadomość AI", context)
    if cost_warning['require_confirmation'] and cost_warning['level'] in ['warning', 'critical']:
        warning_message = create_header("Potwierdzenie kosztu", "warning")
        warning_message += cost_warning['message'] + "\n\nCzy chcesz kontynuować?"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Tak, wyślij", callback_data=f"confirm_message"),
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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
    
    try:
        conversation = await get_active_conversation(user_id)
        conversation_id = conversation['id']
    except Exception as e:
        await update.message.reply_text(get_text("conversation_error", language))
        return
    
    try:
        await save_message(conversation_id, user_id, user_message, is_from_user=True)
    except Exception as e:
        pass
    
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    try:
        history = await get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
    except Exception as e:
        history = []
    
    model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
    
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        user_data = context.chat_data['user_data'][user_id]
        if 'current_model' in user_data:
            model_to_use = user_data['current_model']
            credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
    
    system_prompt = CHAT_MODES[current_mode]["prompt"]
    
    messages = prepare_messages_from_history(history, user_message, system_prompt)
    
    response_message = await update.message.reply_text(get_text("generating_response", language))
    
    full_response = ""
    buffer = ""
    last_update = datetime.datetime.now().timestamp()
    
    try:
        async for chunk in chat_completion_stream(messages, model=model_to_use):
            full_response += chunk
            buffer += chunk
            
            current_time = datetime.datetime.now().timestamp()
            if current_time - last_update >= 1.0 or len(buffer) > 100:
                try:
                    await response_message.edit_text(full_response + "▌", parse_mode=ParseMode.MARKDOWN)
                    buffer = ""
                    last_update = current_time
                except Exception as e:
                    pass
        
        try:
            await response_message.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await response_message.edit_text(full_response)
        
        await save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
        
        await deduct_user_credits(user_id, credit_cost, get_text("message_model", language, model=model_to_use, default=f"Wiadomość ({model_to_use})"))
    except Exception as e:
        await response_message.edit_text(get_text("response_error", language, error=str(e)))
        return
    
    credits = get_user_credits(user_id)
    if credits < 5:
        keyboard = [[InlineKeyboardButton(get_text("buy_credits_btn_with_icon", language, default="🛒 Kup kredyty"), callback_data="menu_credits_buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    await increment_messages_used(user_id)