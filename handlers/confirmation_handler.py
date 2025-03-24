from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from utils.visual_styles import create_header, create_status_indicator
from utils.user_utils import get_user_language
from utils.menu import update_menu
from utils.translations import get_text
from utils.credit_warnings import format_credit_usage_report
from utils.tips import get_random_tip, should_show_tip
from database.credits_client import get_user_credits, check_user_credits, deduct_user_credits
from database.supabase_client import save_message, get_active_conversation, get_conversation_history, increment_messages_used
from utils.openai_client import generate_image_dall_e, analyze_document, analyze_image, chat_completion_stream, prepare_messages_from_history
from config import CREDIT_COSTS, MAX_CONTEXT_MESSAGES, CHAT_MODES
import datetime

async def _process_operation(update, context, operation_type, operation_func, user_id, credit_cost, 
                             process_args, success_handler, error_handler=None):
    """Centralized handler for processing different operations with common flow"""
    language = get_user_language(context, user_id)
    query = update.callback_query
    
    # Check user credits
    credits = get_user_credits(user_id)
    if not check_user_credits(user_id, credit_cost):
        error_msg = create_header("Brak wystarczających kredytów", "error") + \
                    "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów."
        await update_menu(query, error_msg, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]]),
                          parse_mode=ParseMode.MARKDOWN)
        return
    
    credits_before = credits
    
    try:
        # Call the operation function with its arguments
        result = await operation_func(**process_args)
        
        # Deduct credits
        operation_desc = get_text(f"{operation_type}_operation", language, default=operation_type)
        deduct_user_credits(user_id, credit_cost, operation_desc)
        
        credits_after = get_user_credits(user_id)
        
        # Generate usage report
        usage_report = format_credit_usage_report(operation_type, credit_cost, credits_before, credits_after)
        
        # Add tip if needed
        tip_text = ""
        if should_show_tip(user_id, context):
            tip = get_random_tip(operation_type.split('_')[0])  # Get category from operation
            tip_text = f"\n\n💡 *Porada:* {tip}"
        
        # Call success handler with results
        await success_handler(result, usage_report, tip_text)
        
        # Show low credits warning if needed
        if credits_after < 5:
            low_credits_warning = create_header("Niski stan kredytów", "warning") + \
                                f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota."
            
            keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=low_credits_warning,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    except Exception as e:
        if error_handler:
            await error_handler(e)
        else:
            error_msg = create_header(f"Błąd {operation_type}", "error") + \
                      f"Wystąpił błąd podczas operacji: {str(e)}"
            await update_menu(query, error_msg, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]]), 
                             parse_mode=ParseMode.MARKDOWN)

async def handle_image_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje potwierdzenie generowania obrazu"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    if query.data.startswith("confirm_image_"):
        prompt = query.data[14:].replace('_', ' ')
        
        await update_menu(
            query,
            create_status_indicator('loading', "Generowanie obrazu") + "\n\n" +
            f"*Prompt:* {prompt}",
            None,
            parse_mode=ParseMode.MARKDOWN
        )
        
        credit_cost = CREDIT_COSTS["image"]["standard"]
        
        async def success_handler(image_url, usage_report, tip_text):
            caption = create_header("Wygenerowany obraz", "image")
            caption += f"*Prompt:* {prompt}\n\n{usage_report}{tip_text}"
            
            await query.message.delete()
            
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=image_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
        
        async def error_handler(error):
            language = get_user_language(context, user_id)
            
            await update_menu(
                query,
                create_header("Błąd generowania", "error") +
                get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem."),
                parse_mode=ParseMode.MARKDOWN
            )
        
        await _process_operation(
            update, context, "image_generation", generate_image_dall_e, user_id, credit_cost,
            {"prompt": prompt}, success_handler, error_handler
        )
    
    elif query.data == "cancel_operation":
        await update_menu(
            query,
            create_header("Operacja anulowana", "info") +
            "Generowanie obrazu zostało anulowane.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_document_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles confirmation of document operations when cost warning was shown"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_doc_analysis_"):
        document_id = query.data[20:]
        
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or
            'last_document_name' not in context.chat_data['user_data'][user_id]):
            
            await update_menu(
                query,
                create_header("Błąd operacji", "error") +
                "Nie znaleziono informacji o dokumencie. Spróbuj wysłać go ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        file_name = context.chat_data['user_data'][user_id]['last_document_name']
        
        await update_menu(
            query,
            create_status_indicator('loading', "Analizowanie dokumentu") + "\n\n" +
            f"*Dokument:* {file_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        credit_cost = CREDIT_COSTS["document"]
        
        async def success_handler(analysis, usage_report, tip_text):
            result_message = create_header(f"Analiza dokumentu: {file_name}", "document")
            
            analysis_excerpt = analysis[:3000]
            if len(analysis) > 3000:
                analysis_excerpt += "...\n\n(Analiza została skrócona ze względu na długość)"
            
            result_message += analysis_excerpt + f"\n\n{usage_report}{tip_text}"
            
            await update_menu(
                query,
                result_message,
                parse_mode=ParseMode.MARKDOWN
            )
        
        async def document_operation():
            file = await context.bot.get_file(document_id)
            file_bytes = await file.download_as_bytearray()
            return await analyze_document(file_bytes, file_name)
        
        await _process_operation(
            update, context, "document_analysis", document_operation, user_id, credit_cost,
            {}, success_handler
        )

async def handle_photo_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles confirmation of photo operations when cost warning was shown"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_photo_"):
        parts = query.data.split("_")
        if len(parts) >= 4:
            mode = parts[2]
            photo_id = "_".join(parts[3:])
            
            if ('user_data' not in context.chat_data or 
                user_id not in context.chat_data['user_data'] or
                'last_photo_id' not in context.chat_data['user_data'][user_id]):
                
                await update_menu(
                    query,
                    create_header("Błąd operacji", "error") +
                    "Nie znaleziono informacji o zdjęciu. Spróbuj wysłać je ponownie.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            if mode == "translate":
                operation_name = "Tłumaczenie tekstu ze zdjęcia"
                status_message = create_status_indicator('loading', "Tłumaczenie tekstu ze zdjęcia")
            else:
                operation_name = "Analiza zdjęcia"
                status_message = create_status_indicator('loading', "Analizowanie zdjęcia")
            
            await update_menu(
                query,
                status_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            credit_cost = CREDIT_COSTS["photo"]
            
            async def success_handler(result, usage_report, tip_text):
                if mode == "translate":
                    result_message = create_header("Tłumaczenie tekstu ze zdjęcia", "translation")
                else:
                    result_message = create_header("Analiza zdjęcia", "analysis")
                
                result_message += result + f"\n\n{usage_report}{tip_text}"
                
                await update_menu(
                    query,
                    result_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            async def photo_operation():
                file = await context.bot.get_file(photo_id)
                file_bytes = await file.download_as_bytearray()
                return await analyze_image(file_bytes, f"photo_{photo_id}.jpg", mode=mode)
            
            await _process_operation(
                update, context, f"photo_{mode}", photo_operation, user_id, credit_cost,
                {}, success_handler
            )
    
    elif query.data == "cancel_operation":
        await update_menu(
            query,
            create_header("Operacja anulowana", "info") +
            "Operacja została anulowana.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles confirmation of AI message when cost warning was shown"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data == "confirm_message":
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or 
            'pending_message' not in context.chat_data['user_data'][user_id]):
            
            await update_menu(
                query,
                create_header("Błąd operacji", "error") +
                "Nie znaleziono oczekującej wiadomości. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        user_message = context.chat_data['user_data'][user_id]['pending_message']
        
        await query.message.delete()
        
        status_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=create_status_indicator('loading', "Generowanie odpowiedzi"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        current_mode = "no_mode"
        credit_cost = 1
        
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
                current_mode = user_data['current_mode']
                credit_cost = CHAT_MODES[current_mode]["credit_cost"]
        
        try:
            conversation = get_active_conversation(user_id)
            conversation_id = conversation['id']
        except Exception as e:
            await status_message.edit_text(
                create_header("Błąd konwersacji", "error") +
                "Wystąpił błąd przy pobieraniu konwersacji. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            save_message(conversation_id, user_id, user_message, is_from_user=True)
        except Exception as e:
            pass
        
        try:
            history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
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
        
        credits_before = get_user_credits(user_id)
        
        full_response = ""
        buffer = ""
        last_update = datetime.datetime.now().timestamp()
        
        try:
            response_message = await status_message.edit_text(
                create_header("Odpowiedź AI", "chat"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            async for chunk in chat_completion_stream(messages, model=model_to_use):
                full_response += chunk
                buffer += chunk
                
                current_time = datetime.datetime.now().timestamp()
                if current_time - last_update >= 1.0 or len(buffer) > 100:
                    try:
                        await response_message.edit_text(
                            create_header("Odpowiedź AI", "chat") + full_response + "▌",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        buffer = ""
                        last_update = current_time
                    except Exception as e:
                        pass
            
            try:
                await response_message.edit_text(
                    create_header("Odpowiedź AI", "chat") + full_response,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                await response_message.edit_text(
                    create_header("Odpowiedź AI", "chat") + full_response,
                    parse_mode=None
                )
            
            save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
            
            deduct_user_credits(user_id, credit_cost, 
                               get_text("message_model", language, model=model_to_use, default=f"Wiadomość ({model_to_use})"))
            
            credits_after = get_user_credits(user_id)
            
            usage_report = format_credit_usage_report(
                "Wiadomość AI", 
                credit_cost, 
                credits_before, 
                credits_after
            )
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=usage_report,
                parse_mode=ParseMode.MARKDOWN
            )
            
            if credits_after < 5:
                low_credits_warning = create_header("Niski stan kredytów", "warning")
                low_credits_warning += f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota."
                
                keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=low_credits_warning,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            
            tip = get_contextual_tip('chat', context, user_id)
            if tip:
                tip_message = f"💡 *Porada:* {tip}"
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=tip_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            increment_messages_used(user_id)
            
        except Exception as e:
            await status_message.edit_text(
                create_header("Błąd odpowiedzi", "error") +
                get_text("response_error", language, error=str(e)),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cancel_operation":
        await update_menu(
            query,
            create_header("Operacja anulowana", "info") +
            "Wysłanie wiadomości zostało anulowane.",
            parse_mode=ParseMode.MARKDOWN
        )