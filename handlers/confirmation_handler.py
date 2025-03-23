from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.visual_styles import create_header, create_status_indicator
from utils.user_utils import get_user_language
from utils.translations import get_text
from utils.credit_warnings import format_credit_usage_report
from utils.tips import get_random_tip, should_show_tip, get_contextual_tip
from database.credits_client import get_user_credits, check_user_credits, deduct_user_credits
from database.supabase_client import save_message, get_active_conversation, get_conversation_history, increment_messages_used
from utils.openai_client import generate_image_dall_e, analyze_document, analyze_image, chat_completion_stream, prepare_messages_from_history
from config import CREDIT_COSTS, MAX_CONTEXT_MESSAGES, CHAT_MODES
import datetime

async def handle_image_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles confirmation of image generation when cost warning was shown
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_image_"):
        # Extract prompt from callback data
        prompt = query.data[14:].replace('_', ' ')
        
        # Inform the user that image generation has started
        await query.edit_message_text(
            create_status_indicator('loading', "Generowanie obrazu") + "\n\n" +
            f"*Prompt:* {prompt}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Get quality and cost
        quality = "standard"
        credit_cost = CREDIT_COSTS["image"][quality]
        
        # Check if the user still has enough credits
        credits = get_user_credits(user_id)
        if not check_user_credits(user_id, credit_cost):
            await query.edit_message_text(
                create_header("Brak wystarczających kredytów", "error") +
                "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store credits before the operation for reporting
        credits_before = credits
        
        # Generate image
        image_url = await generate_image_dall_e(prompt)
        
        # Deduct credits
        deduct_user_credits(user_id, credit_cost, get_text("image_generation", language, default="Generowanie obrazu"))
        
        # Get credits after the operation
        credits_after = get_user_credits(user_id)
        
        if image_url:
            # Prepare a caption with usage report
            caption = create_header("Wygenerowany obraz", "image")
            caption += f"*Prompt:* {prompt}\n"
            
            # Add credit usage report
            usage_report = format_credit_usage_report(
                "Generowanie obrazu", 
                credit_cost, 
                credits_before, 
                credits_after
            )
            caption += f"\n{usage_report}"
            
            # Add a tip if appropriate
            if should_show_tip(user_id, context):
                tip = get_random_tip('image')
                caption += f"\n\n💡 *Porada:* {tip}"
            
            # Delete the confirmation message
            await query.message.delete()
            
            # Send the image
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=image_url,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Update with error message
            await query.edit_message_text(
                create_header("Błąd generowania", "error") +
                get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem."),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cancel_operation":
        # User canceled the operation
        await query.edit_message_text(
            create_header("Operacja anulowana", "info") +
            "Generowanie obrazu zostało anulowane.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_document_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles confirmation of document operations when cost warning was shown
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_doc_analysis_"):
        # Extract document_id from callback data
        document_id = query.data[20:]
        
        # Check if document info is in context
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or
            'last_document_name' not in context.chat_data['user_data'][user_id]):
            
            await query.edit_message_text(
                create_header("Błąd operacji", "error") +
                "Nie znaleziono informacji o dokumencie. Spróbuj wysłać go ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        file_name = context.chat_data['user_data'][user_id]['last_document_name']
        
        # Inform the user that analysis has started
        await query.edit_message_text(
            create_status_indicator('loading', "Analizowanie dokumentu") + "\n\n" +
            f"*Dokument:* {file_name}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Get operation cost
        credit_cost = CREDIT_COSTS["document"]
        
        # Check if the user still has enough credits
        credits = get_user_credits(user_id)
        if not check_user_credits(user_id, credit_cost):
            await query.edit_message_text(
                create_header("Brak wystarczających kredytów", "error") +
                "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store credits before the operation for reporting
        credits_before = credits
        
        # Pobierz plik
        try:
            file = await context.bot.get_file(document_id)
            file_bytes = await file.download_as_bytearray()
            
            # Analyze document
            analysis = await analyze_document(file_bytes, file_name)
            
            # Deduct credits
            deduct_user_credits(user_id, credit_cost, f"Analiza dokumentu: {file_name}")
            
            # Get credits after the operation
            credits_after = get_user_credits(user_id)
            
            # Prepare result message with styled header
            result_message = create_header(f"Analiza dokumentu: {file_name}", "document")
            
            # Add an excerpt from the analysis (first 3000 characters)
            analysis_excerpt = analysis[:3000]
            if len(analysis) > 3000:
                analysis_excerpt += "...\n\n(Analiza została skrócona ze względu na długość)"
            
            result_message += analysis_excerpt
            
            # Add credit usage report
            usage_report = format_credit_usage_report(
                "Analiza dokumentu", 
                credit_cost, 
                credits_before, 
                credits_after
            )
            result_message += f"\n\n{usage_report}"
            
            # Add a tip if appropriate
            if should_show_tip(user_id, context):
                tip = get_random_tip('document')
                result_message += f"\n\n💡 *Porada:* {tip}"
            
            # Update the message with analysis results
            await query.edit_message_text(
                result_message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Error analyzing document: {e}")
            await query.edit_message_text(
                create_header("Błąd analizy", "error") +
                "Wystąpił błąd podczas analizowania dokumentu. Spróbuj ponownie później.",
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_photo_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles confirmation of photo operations when cost warning was shown
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data.startswith("confirm_photo_"):
        # Extract mode and photo_id from callback data
        parts = query.data.split("_")
        if len(parts) >= 4:
            mode = parts[2]
            photo_id = "_".join(parts[3:])
            
            # Check if photo info is in context
            if ('user_data' not in context.chat_data or 
                user_id not in context.chat_data['user_data'] or
                'last_photo_id' not in context.chat_data['user_data'][user_id]):
                
                await query.edit_message_text(
                    create_header("Błąd operacji", "error") +
                    "Nie znaleziono informacji o zdjęciu. Spróbuj wysłać je ponownie.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Get operation name and message
            if mode == "translate":
                operation_name = "Tłumaczenie tekstu ze zdjęcia"
                status_message = create_status_indicator('loading', "Tłumaczenie tekstu ze zdjęcia")
            else:
                operation_name = "Analiza zdjęcia"
                status_message = create_status_indicator('loading', "Analizowanie zdjęcia")
            
            # Inform the user that the operation has started
            await query.edit_message_text(
                status_message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Get operation cost
            credit_cost = CREDIT_COSTS["photo"]
            
            # Check if the user still has enough credits
            credits = get_user_credits(user_id)
            if not check_user_credits(user_id, credit_cost):
                await query.edit_message_text(
                    create_header("Brak wystarczających kredytów", "error") +
                    "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Store credits before the operation for reporting
            credits_before = credits
            
            try:
                # Get the photo
                file = await context.bot.get_file(photo_id)
                file_bytes = await file.download_as_bytearray()
                
                # Analyze or translate the photo
                result = await analyze_image(file_bytes, f"photo_{photo_id}.jpg", mode=mode)
                
                # Deduct credits
                deduct_user_credits(user_id, credit_cost, operation_name)
                
                # Get credits after the operation
                credits_after = get_user_credits(user_id)
                
                # Prepare result message with styled header
                if mode == "translate":
                    result_message = create_header("Tłumaczenie tekstu ze zdjęcia", "translation")
                else:
                    result_message = create_header("Analiza zdjęcia", "analysis")
                
                # Add the result
                result_message += result
                
                # Add credit usage report
                usage_report = format_credit_usage_report(
                    operation_name, 
                    credit_cost, 
                    credits_before, 
                    credits_after
                )
                result_message += f"\n\n{usage_report}"
                
                # Add a tip if appropriate
                if should_show_tip(user_id, context):
                    tip = get_random_tip('document')
                    result_message += f"\n\n💡 *Porada:* {tip}"
                
                # Update the message with results
                await query.edit_message_text(
                    result_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                print(f"Error processing photo: {e}")
                await query.edit_message_text(
                    create_header("Błąd operacji", "error") +
                    f"Wystąpił błąd podczas {operation_name.lower()}. Spróbuj ponownie później.",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    elif query.data == "cancel_operation":
        # User canceled the operation
        await query.edit_message_text(
            create_header("Operacja anulowana", "info") +
            "Operacja została anulowana.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles confirmation of AI message when cost warning was shown
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data == "confirm_message":
        # Check if there's a pending message
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or 
            'pending_message' not in context.chat_data['user_data'][user_id]):
            
            await query.edit_message_text(
                create_header("Błąd operacji", "error") +
                "Nie znaleziono oczekującej wiadomości. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Get the pending message
        user_message = context.chat_data['user_data'][user_id]['pending_message']
        
        # Delete confirmation message to avoid clutter
        await query.message.delete()
        
        # Update loading status
        status_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=create_status_indicator('loading', "Generowanie odpowiedzi"),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Determine mode and credit cost (same logic as in message_handler)
        current_mode = "no_mode"
        credit_cost = 1
        
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
                current_mode = user_data['current_mode']
                credit_cost = CHAT_MODES[current_mode]["credit_cost"]
        
        # Get or create conversation
        try:
            conversation = get_active_conversation(user_id)
            conversation_id = conversation['id']
        except Exception as e:
            print(f"Błąd przy pobieraniu konwersacji: {e}")
            await status_message.edit_text(
                create_header("Błąd konwersacji", "error") +
                "Wystąpił błąd przy pobieraniu konwersacji. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Save user message to database
        try:
            save_message(conversation_id, user_id, user_message, is_from_user=True)
        except Exception as e:
            print(f"Błąd przy zapisie wiadomości użytkownika: {e}")
        
        # Get conversation history
        try:
            history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
        except Exception as e:
            print(f"Błąd przy pobieraniu historii: {e}")
            history = []
        
        # Determine model to use
        model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
        
        # If user selected a specific model, use it
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'current_model' in user_data:
                model_to_use = user_data['current_model']
                # Update credit cost based on model
                credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
        
        # Prepare system prompt from selected mode
        system_prompt = CHAT_MODES[current_mode]["prompt"]
        
        # Prepare messages for OpenAI API
        messages = prepare_messages_from_history(history, user_message, system_prompt)
        
        # Store credits before operation
        credits_before = get_user_credits(user_id)
        
        # Generate response
        full_response = ""
        buffer = ""
        last_update = datetime.datetime.now().timestamp()
        
        try:
            # Update message with starting response
            response_message = await status_message.edit_text(
                create_header("Odpowiedź AI", "chat"),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Stream the response
            async for chunk in chat_completion_stream(messages, model=model_to_use):
                full_response += chunk
                buffer += chunk
                
                # Update message periodically
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
                        print(f"Błąd przy aktualizacji wiadomości: {e}")
            
            # Final update without cursor
            try:
                await response_message.edit_text(
                    create_header("Odpowiedź AI", "chat") + full_response,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                print(f"Błąd formatowania Markdown: {e}")
                await response_message.edit_text(
                    create_header("Odpowiedź AI", "chat") + full_response,
                    parse_mode=None
                )
            
            # Save response to database
            save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model_to_use)
            
            # Deduct credits
            deduct_user_credits(user_id, credit_cost, 
                               get_text("message_model", language, model=model_to_use, default=f"Wiadomość ({model_to_use})"))
            
            # Get credits after operation
            credits_after = get_user_credits(user_id)
            
            # Display credit usage report
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
            
            # Check for low credits
            if credits_after < 5:
                low_credits_warning = create_header("Niski stan kredytów", "warning")
                low_credits_warning += f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota."
                
                # Add buttons to buy credits
                keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=low_credits_warning,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            
            # Add tip if appropriate
            tip = get_contextual_tip('chat', context, user_id)
            if tip:
                tip_message = f"💡 *Porada:* {tip}"
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=tip_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Increment message counter
            increment_messages_used(user_id)
            
        except Exception as e:
            print(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
            await status_message.edit_text(
                create_header("Błąd odpowiedzi", "error") +
                get_text("response_error", language, error=str(e)),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cancel_operation":
        # User canceled the message
        await query.edit_message_text(
            create_header("Operacja anulowana", "info") +
            "Wysłanie wiadomości zostało anulowane.",
            parse_mode=ParseMode.MARKDOWN
        )