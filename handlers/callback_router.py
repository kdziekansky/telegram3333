# handlers/callback_router.py
"""
Centralized callback routing to prevent conflicts between handlers
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.user_utils import get_user_language
from utils.menu import update_menu, store_menu_state
from utils.translations import get_text
from config import CHAT_MODES, AVAILABLE_MODELS, CREDIT_COSTS, DEFAULT_MODEL

logger = logging.getLogger(__name__)

async def route_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main callback router that routes callbacks to appropriate handlers
    
    Args:
        update: Update object
        context: Context object
        
    Returns:
        bool: Whether the callback was handled
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Log the callback for debugging
    logger.debug(f"Received callback: {query.data} from user {user_id}")
    
    # First, acknowledge the callback to remove waiting state
    await query.answer()
    
    # Menu section callbacks
    if query.data.startswith("menu_section_") or query.data == "menu_image_generate" or query.data == "menu_help":
        return await route_menu_section_callback(update, context)
    
    # Menu back callbacks
    elif query.data == "menu_back_main":
        return await route_back_to_main_callback(update, context)
    
    # Credits callbacks
    elif query.data.startswith("menu_credits_") or query.data.startswith("credits_"):
        return await route_credits_callback(update, context)
    
    # Model selection callbacks
    elif query.data == "settings_model" or query.data.startswith("model_"):
        return await route_model_selection_callback(update, context)
    
    # Language selection callbacks
    elif query.data == "settings_language" or query.data.startswith("start_lang_"):
        return await route_language_selection_callback(update, context)
    
    # Chat mode callbacks
    elif query.data.startswith("mode_"):
        return await route_mode_selection_callback(update, context)
    
    # Quick action callbacks
    elif query.data.startswith("quick_"):
        return await route_quick_action_callback(update, context)
    
    # Payment and subscription callbacks
    elif (query.data.startswith("payment_") or query.data.startswith("buy_package_") 
        or query.data == "subscription_command" or query.data == "transactions_command" or 
        query.data.startswith("cancel_subscription_")):
        return await route_payment_callback(update, context)
    
    # Onboarding callbacks
    elif query.data.startswith("onboarding_"):
        return await route_onboarding_callback(update, context)
    
    # Image confirmation callbacks
    elif query.data.startswith("confirm_image_") or query.data == "cancel_operation":
        return await route_image_confirmation_callback(update, context)
    
    # Document confirmation callbacks
    elif query.data.startswith("confirm_doc_") or query.data.startswith("analyze_document") or query.data.startswith("translate_document"):
        return await route_document_callback(update, context)
    
    # Photo confirmation callbacks
    elif query.data.startswith("confirm_photo_") or query.data == "analyze_photo" or query.data == "translate_photo":
        return await route_photo_callback(update, context)
    
    # Message confirmation callbacks
    elif query.data == "confirm_message" or query.data == "cancel_operation":
        return await route_message_confirmation_callback(update, context)
    
    # History callbacks
    elif query.data.startswith("history_"):
        return await route_history_callback(update, context)
    
    # Settings callbacks
    elif query.data.startswith("settings_"):
        return await route_settings_callback(update, context)
        
    # Help section callbacks
    elif query.data.startswith("help_"):
        return await route_help_callback(update, context)
    
    # Unknown callback
    logger.warning(f"Unhandled callback: {query.data}")
    try:
        keyboard = [[InlineKeyboardButton("⬅️ " + get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")]]
        await update_menu(
            query,
            f"Nieznany przycisk. Spróbuj ponownie później.",
            InlineKeyboardMarkup(keyboard)
        )
        return True
    except Exception as e:
        logger.error(f"Error displaying message about unhandled callback: {e}")
        return False


# Dodaj funkcję do routowania callbacków pomocy
async def route_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes help-related callbacks"""
    from handlers.menu_handler import handle_help_callbacks
    return await handle_help_callbacks(update, context)


# Routing implementations
async def route_menu_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes menu section callbacks"""
    query = update.callback_query
    
    if query.data == "menu_section_chat_modes":
        from handlers.menu_handler import handle_chat_modes_section
        return await handle_chat_modes_section(update, context)
    elif query.data == "menu_section_credits":
        from handlers.menu_handler import handle_credits_section
        return await handle_credits_section(update, context)
    elif query.data == "menu_section_history":
        from handlers.menu_handler import handle_history_section
        return await handle_history_section(update, context)
    elif query.data == "menu_section_settings":
        from handlers.menu_handler import handle_settings_section
        return await handle_settings_section(update, context)
    elif query.data == "menu_help":
        from handlers.menu_handler import handle_help_section
        return await handle_help_section(update, context)
    elif query.data == "menu_image_generate":
        from handlers.menu_handler import handle_image_section
        return await handle_image_section(update, context)
    
    return False

async def route_back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes back to main menu callbacks"""
    from handlers.menu_handler import handle_back_to_main
    return await handle_back_to_main(update, context)

async def route_credits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes credits-related callbacks"""
    from handlers.credit_handler import handle_credit_callback
    return await handle_credit_callback(update, context)

async def route_model_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes model selection callbacks"""
    query = update.callback_query
    
    if query.data == "settings_model":
        from handlers.menu_handler import handle_model_selection
        return await handle_model_selection(update, context)
    elif query.data.startswith("model_"):
        # Implement model selection logic directly here to avoid circular imports
        user_id = query.from_user.id
        language = get_user_language(context, user_id)
        model_id = query.data[6:]  # Remove 'model_' prefix
        
        # Save model in context
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['current_model'] = model_id
        
        # Mark chat as initialized
        from utils.user_utils import mark_chat_initialized
        mark_chat_initialized(context, user_id)
        
        # Get credit cost for the selected model
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        
        # Notify user about model change
        model_name = AVAILABLE_MODELS.get(model_id, "Unknown model")
        message = f"Wybrany model: *{model_name}*\nKoszt: *{credit_cost}* kredyt(ów) za wiadomość\n\nMożesz teraz zadać pytanie."
        
        # Return buttons
        keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Handle both text messages and messages with caption
            is_caption = hasattr(query.message, 'caption') and query.message.caption is not None
            
            if is_caption:
                await query.edit_message_caption(
                    caption=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            return True
        except Exception as e:
            logger.error(f"Error updating model confirmation: {e}")
            # In case of error, send a new message
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return True
    
    return False

async def route_language_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes language selection callbacks"""
    query = update.callback_query
    
    if query.data == "settings_language":
        from handlers.menu_handler import handle_language_selection
        return await handle_language_selection(update, context)
    elif query.data.startswith("start_lang_"):
        from handlers.start_handler import handle_language_selection
        return await handle_language_selection(update, context)
    
    return False

async def route_mode_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes chat mode selection callbacks"""
    from handlers.mode_handler import handle_mode_selection
    query = update.callback_query
    mode_id = query.data[5:]  # Remove 'mode_' prefix
    return await handle_mode_selection(update, context, mode_id)

async def route_quick_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes quick action callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    if query.data == "quick_new_chat":
        # Handle new chat creation
        try:
            # Dodane await przed create_new_conversation
            from database.supabase_client import create_new_conversation
            from utils.user_utils import mark_chat_initialized
            
            conversation = await create_new_conversation(user_id)
            mark_chat_initialized(context, user_id)
            
            await query.answer(get_text("new_chat_created", language))
            
            # Close the menu
            await query.message.delete()
            
            # Determine current mode and cost
            from config import DEFAULT_MODEL, AVAILABLE_MODELS, CHAT_MODES, CREDIT_COSTS
            
            # Default values
            current_mode = "no_mode"
            model_to_use = DEFAULT_MODEL
            credit_cost = CREDIT_COSTS["message"].get(model_to_use, 1)
            
            # Get user's selected mode if available
            if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
                user_data = context.chat_data['user_data'][user_id]
                
                # Check for current mode
                if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
                    current_mode = user_data['current_mode']
                    model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
                    credit_cost = CHAT_MODES[current_mode]["credit_cost"]
                
                # Check for current model (overrides mode's model)
                if 'current_model' in user_data and user_data['current_model'] in AVAILABLE_MODELS:
                    model_to_use = user_data['current_model']
                    credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
            
            # Get friendly model name
            model_name = AVAILABLE_MODELS.get(model_to_use, model_to_use)
            
            # Create new chat message with model info
            base_message = get_text("new_chat_created_message", language, default="✅ Utworzono nową rozmowę. Możesz zacząć pisać! ")
            model_info = get_text("model_info", language, model=model_name, cost=credit_cost, default=f"Używasz modelu {model_name} za {credit_cost} kredyt(ów) za wiadomość")
            
            # Single button - model selection (zmiana callback_data)
            keyboard = [
                [InlineKeyboardButton("🤖 " + get_text("select_model", language, default="Wybierz model czatu"), callback_data="menu_section_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send confirmation message
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=base_message + model_info,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.error(f"Error creating new chat: {e}")
            import traceback
            traceback.print_exc()
            
            # Wysyłamy prosty komunikat bez próby połączenia z bazą
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=get_text("offline_new_chat", language, default="Utworzono nową rozmowę (tryb offline).")
            )
            return True
            
    elif query.data == "quick_last_chat":
        try:
            # Get active conversation - Dodane await
            from database.supabase_client import get_active_conversation
            
            # Próba pobrania konwersacji - jeśli się nie uda, obsługujemy błąd
            try:
                conversation = await get_active_conversation(user_id)
            except Exception as e:
                # W przypadku błędu używamy trybu offline
                logger.warning(f"Cannot access database, using offline mode: {e}")
                conversation = None
            
            if conversation:
                await query.answer(get_text("returning_to_last_chat", language, default="Powrót do ostatniej rozmowy"))
                
                # Close menu
                await query.message.delete()
            else:
                await query.answer(get_text("no_active_chat", language, default="Brak aktywnej rozmowy"))
                
                # Create new conversation - Dodane await
                from database.supabase_client import create_new_conversation
                try:
                    await create_new_conversation(user_id)
                except Exception as e:
                    logger.warning(f"Error creating conversation (offline mode): {e}")
                
                # Close menu
                await query.message.delete()
                
                # Send message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=get_text("new_chat_created_message", language, default="Utworzono nową konwersację, ponieważ nie znaleziono aktywnej.")
                )
            return True
        except Exception as e:
            logger.error(f"Error handling last chat: {e}")
            import traceback
            traceback.print_exc()
            
            # Zapasowa obsługa błędu - po prostu wysyłamy wiadomość
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=get_text("offline_mode_active", language, default="Tryb offline aktywny - możesz nadal korzystać z bota.")
            )
            return True
            
    elif query.data == "quick_buy_credits":
        try:
            # Redirect to credit purchase
            from handlers.credit_handler import buy_command
            
            # Create fake update object
            fake_update = type('obj', (object,), {'effective_user': query.from_user, 'message': query.message})
            
            # Delete original message
            await query.message.delete()
            
            await buy_command(fake_update, context)
            return True
        except Exception as e:
            logger.error(f"Error redirecting to credit purchase: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return False

async def route_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes payment and subscription callbacks"""
    try:
        from handlers.payment_handler import handle_payment_callback
        return await handle_payment_callback(update, context)
    except Exception as e:
        logger.error(f"Error in payment callback handling: {e}")
        return False

async def route_onboarding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes onboarding callbacks"""
    try:
        from handlers.onboarding_handler import handle_onboarding_callback
        return await handle_onboarding_callback(update, context)
    except Exception as e:
        logger.error(f"Error in onboarding callback handling: {e}")
        return False

async def route_image_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes image confirmation callbacks"""
    try:
        from handlers.confirmation_handler import handle_image_confirmation
        return await handle_image_confirmation(update, context)
    except Exception as e:
        logger.error(f"Error in image confirmation callback handling: {e}")
        return False

async def route_document_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes document-related callbacks"""
    query = update.callback_query
    
    if query.data.startswith("confirm_doc_"):
        try:
            from handlers.confirmation_handler import handle_document_confirmation
            return await handle_document_confirmation(update, context)
        except Exception as e:
            logger.error(f"Error in document confirmation callback handling: {e}")
            return False
    elif query.data in ["analyze_document", "translate_document"]:
        try:
            from handlers.file_handler import handle_document
            # Create a fake update with document information
            if 'user_data' in context.chat_data and query.from_user.id in context.chat_data['user_data']:
                user_data = context.chat_data['user_data'][query.from_user.id]
                if 'last_document_id' in user_data:
                    # TODO: Implement proper document analysis based on callback
                    # For now, just show a message
                    await query.message.reply_text("Funkcja analizy dokumentu w trakcie implementacji.")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error in document analysis callback handling: {e}")
            return False
    
    return False

async def route_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes photo-related callbacks"""
    query = update.callback_query
    
    if query.data.startswith("confirm_photo_"):
        try:
            from handlers.confirmation_handler import handle_photo_confirmation
            return await handle_photo_confirmation(update, context)
        except Exception as e:
            logger.error(f"Error in photo confirmation callback handling: {e}")
            return False
    elif query.data in ["analyze_photo", "translate_photo"]:
        try:
            from handlers.file_handler import handle_photo
            # Create a fake update with photo information
            if 'user_data' in context.chat_data and query.from_user.id in context.chat_data['user_data']:
                user_data = context.chat_data['user_data'][query.from_user.id]
                if 'last_photo_id' in user_data:
                    # TODO: Implement proper photo analysis based on callback
                    # For now, just show a message
                    await query.message.reply_text("Funkcja analizy zdjęcia w trakcie implementacji.")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error in photo analysis callback handling: {e}")
            return False
    
    return False

async def route_message_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes message confirmation callbacks"""
    try:
        from handlers.confirmation_handler import handle_message_confirmation
        return await handle_message_confirmation(update, context)
    except Exception as e:
        logger.error(f"Error in message confirmation callback handling: {e}")
        return False

async def route_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes history-related callbacks"""
    try:
        from handlers.menu_handler import handle_history_callbacks
        return await handle_history_callbacks(update, context)
    except Exception as e:
        logger.error(f"Error in history callback handling: {e}")
        return False

# Dodaj do handlers/menu_handler.py
async def handle_help_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje callbacki związane z sekcją pomocy"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    from config import BOT_NAME
    from database.credits_client import get_user_credits
    
    if query.data == "help_commands":
        # Lista komend
        commands_text = """
*Lista dostępnych komend:*

• /start - Rozpocznij korzystanie z bota
• /credits - Sprawdź stan kredytów
• /buy - Kup pakiet kredytów
• /status - Sprawdź status konta
• /newchat - Rozpocznij nową konwersację
• /mode - Wybierz tryb czatu
• /models - Wybierz model AI
• /image [opis] - Wygeneruj obraz
• /export - Eksportuj konwersację do PDF
• /theme - Zarządzaj tematami konwersacji
• /remind [czas] [treść] - Ustaw przypomnienie
• /code [kod] - Aktywuj kod promocyjny
• /creditstats - Analiza wykorzystania kredytów
• /restart - Zrestartuj informacje o bocie
• /menu - Pokaż menu główne
        """
        
        keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(query, commands_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        return True
        
    elif query.data == "help_credits":
        # Informacje o kredytach
        credits = get_user_credits(user_id)
        
        credits_text = f"""
*Informacje o systemie kredytów:*

• Aktualna liczba kredytów: *{credits}*
• Kredyty są używane do wszystkich operacji w bocie

*Koszty operacji:*
• Wiadomość standardowa (GPT-3.5): 1 kredyt
• Wiadomość premium (GPT-4o): 3 kredyty
• Wiadomość ekspercka (GPT-4): 5 kredytów
• Generowanie obrazu: 10-15 kredytów
• Analiza dokumentu: 5 kredytów
• Analiza zdjęcia: 8 kredytów

Użyj /buy aby dokupić kredyty lub /creditstats aby sprawdzić statystyki wykorzystania.
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 Kup kredyty", callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ Powrót", callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(query, credits_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        return True
        
    elif query.data == "help_contact":
        # Informacje kontaktowe
        contact_text = f"""
*Kontakt i wsparcie:*

• Email: support@{BOT_NAME.lower()}.ai
• Telegram: @{BOT_NAME.lower()}_support
• Czas odpowiedzi: do 24h w dni robocze

*Zgłaszanie błędów:*
Jeśli napotkasz problem, opisz dokładnie co się stało i w jakich okolicznościach.

*Sugestie:*
Chętnie przyjmujemy pomysły na nowe funkcje!
        """
        
        keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(query, contact_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        return True
        
    return False

async def route_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes settings-related callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "settings_name":
        # Implement name settings here
        message_text = get_text("settings_change_name", language, default="Aby zmienić swoją nazwę, użyj komendy /setname [twoja_nazwa].\n\nNa przykład: /setname Jan Kowalski")
        keyboard = [[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(
            query,
            message_text,
            reply_markup,
            parse_mode="Markdown"
        )
        return True
    else:
        # For all other settings callbacks
        try:
            from handlers.menu_handler import handle_settings_callbacks
            return await handle_settings_callbacks(update, context)
        except Exception as e:
            logger.error(f"Error in settings callback handling: {e}")
            return False