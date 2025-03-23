from telegram import Update
from utils.translations import get_text
from handlers.menu_handler import get_user_language
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.supabase_client import check_active_subscription
from utils.openai_client import analyze_document, analyze_image
from utils.ui_elements import info_card, section_divider, feature_badge, progress_bar
from utils.visual_styles import style_message, create_header, create_section, create_status_indicator
from utils.tips import get_random_tip, should_show_tip
from utils.credit_warnings import check_operation_cost, format_credit_usage_report
import asyncio

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych dokumentów z ulepszoną prezentacją"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if not check_active_subscription(user_id):
        # Enhanced subscription expired message
        message = create_header("Subskrypcja wygasła", "warning")
        message += (
            "Twoja subskrypcja wygasła lub nie masz wystarczającej liczby kredytów, "
            "aby wykonać tę operację. Kup pakiet kredytów, aby kontynuować."
        )
        
        # Add buttons to buy credits
        keyboard = [
            [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    document = update.message.document
    file_name = document.file_name
    
    # Get credits information
    credit_cost = CREDIT_COSTS["document"]
    credits = get_user_credits(user_id)
    
    # Check if the user has enough credits
    if not check_user_credits(user_id, credit_cost):
        # Enhanced credit warning
        warning_message = create_header("Brak wystarczających kredytów", "warning")
        warning_message += (
            f"Nie masz wystarczającej liczby kredytów, aby przeanalizować dokument.\n\n"
            f"▪️ Koszt operacji: *{credit_cost}* kredytów\n"
            f"▪️ Twój stan kredytów: *{credits}* kredytów\n\n"
            f"Potrzebujesz jeszcze *{credit_cost - credits}* kredytów."
        )
        
        # Add buttons to buy credits
        keyboard = [
            [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            warning_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Sprawdź rozmiar pliku (limit 25MB)
    if document.file_size > 25 * 1024 * 1024:
        # Enhanced file size error message
        error_message = create_header("Plik zbyt duży", "error")
        error_message += (
            "Maksymalny rozmiar pliku to 25MB. Twój plik ma "
            f"{document.file_size / (1024 * 1024):.1f}MB. "
            "Spróbuj zmniejszyć rozmiar pliku lub podzielić go na mniejsze części."
        )
        
        await update.message.reply_text(
            error_message,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check caption to determine the operation
    caption = update.message.caption or ""
    caption_lower = caption.lower()
    
    # Determine operation type based on caption and file type
    is_pdf = file_name.lower().endswith('.pdf')
    
    # If file is PDF and user mentions translation
    if is_pdf and any(word in caption_lower for word in ["tłumacz", "przetłumacz", "translate", "переводить"]):
        # Show operation options with buttons
        options_message = create_header("Opcje dla dokumentu PDF", "document")
        options_message += (
            f"Wykryto dokument PDF: *{file_name}*\n\n"
            f"Wybierz co chcesz zrobić z tym dokumentem:"
        )
        
        # Show operation costs
        options_message += "\n\n" + create_section("Koszt operacji", 
            f"▪️ Analiza dokumentu: *{CREDIT_COSTS['document']}* kredytów\n"
            f"▪️ Tłumaczenie dokumentu: *8* kredytów")
        
        # Add a tip if appropriate
        if should_show_tip(user_id, context):
            tip = get_random_tip('document')
            options_message += f"\n\n💡 *Porada:* {tip}"
        
        # Create buttons for different operations
        keyboard = [
            [
                InlineKeyboardButton("📝 Analiza dokumentu", callback_data="analyze_document"),
                InlineKeyboardButton("🔤 Tłumaczenie dokumentu", callback_data="translate_document")
            ],
            [
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            options_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Save document info in context for later use
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
            
        context.chat_data['user_data'][user_id]['last_document_id'] = document.file_id
        context.chat_data['user_data'][user_id]['last_document_name'] = file_name
        
        return
    
    # If no caption or not a special case, proceed with standard analysis
    # Check operation cost and show warning if needed
    cost_warning = check_operation_cost(user_id, credit_cost, credits, "Analiza dokumentu", context)
    if cost_warning['require_confirmation'] and cost_warning['level'] in ['warning', 'critical']:
        # Show warning and ask for confirmation
        warning_message = create_header("Potwierdzenie kosztu", "warning")
        warning_message += cost_warning['message'] + "\n\nCzy chcesz kontynuować?"
        
        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Tak, analizuj", callback_data=f"confirm_doc_analysis_{document.file_id}"),
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            warning_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Save document info in context for later use
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
            
        context.chat_data['user_data'][user_id]['last_document_id'] = document.file_id
        context.chat_data['user_data'][user_id]['last_document_name'] = file_name
        
        return
    
    # Proceed with analysis if no confirmation needed
    # Wyślij informację o rozpoczęciu analizy
    message = await update.message.reply_text(
        create_status_indicator('loading', "Analizowanie dokumentu") + "\n\n" +
        f"*Dokument:* {file_name}"
    )
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Store credits before the operation for reporting
    credits_before = credits
    
    # Pobierz plik
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj plik
    analysis = await analyze_document(file_bytes, file_name)
    
    # Odejmij kredyty
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
    
    # Wyślij analizę do użytkownika
    await message.edit_text(
        result_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź aktualny stan kredytów
    if credits_after < 5:
        low_credits_warning = create_header("Niski stan kredytów", "warning")
        low_credits_warning += f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota."
        
        # Add buttons to buy credits
        keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            low_credits_warning,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa przesłanych zdjęć z ulepszoną prezentacją"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if not check_active_subscription(user_id):
        # Enhanced subscription expired message
        message = create_header("Subskrypcja wygasła", "warning")
        message += (
            "Twoja subskrypcja wygasła lub nie masz wystarczającej liczby kredytów, "
            "aby wykonać tę operację. Kup pakiet kredytów, aby kontynuować."
        )
        
        # Add buttons to buy credits
        keyboard = [
            [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Get credits information
    credit_cost = CREDIT_COSTS["photo"]
    credits = get_user_credits(user_id)
    
    # Wybierz zdjęcie o najwyższej rozdzielczości
    photo = update.message.photo[-1]
    
    # Get caption to determine operation
    caption = update.message.caption or ""
    
    # If no caption, show options
    if not caption:
        # Show operation options with buttons
        options_message = create_header("Opcje dla zdjęcia", "image")
        options_message += (
            "Wykryto zdjęcie. Wybierz co chcesz zrobić z tym zdjęciem:"
        )
        
        # Show operation costs
        options_message += "\n\n" + create_section("Koszt operacji", 
            f"▪️ Analiza zdjęcia: *{CREDIT_COSTS['photo']}* kredytów\n"
            f"▪️ Tłumaczenie tekstu: *{CREDIT_COSTS['photo']}* kredytów")
        
        # Add a tip if appropriate
        if should_show_tip(user_id, context):
            tip = get_random_tip('document')
            options_message += f"\n\n💡 *Porada:* {tip}"
        
        # Create buttons for different operations
        keyboard = [
            [
                InlineKeyboardButton("🔍 Analiza zdjęcia", callback_data="analyze_photo"),
                InlineKeyboardButton("🔤 Tłumaczenie tekstu", callback_data="translate_photo")
            ],
            [
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            options_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Save photo info in context for later use
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
            
        context.chat_data['user_data'][user_id]['last_photo_id'] = photo.file_id
        
        return
    
    # Determine operation based on caption
    caption_lower = caption.lower()
    
    # Check for translation intent
    if any(word in caption_lower for word in ["tłumacz", "przetłumacz", "translate", "переводить"]):
        mode = "translate"
        operation_name = "Tłumaczenie tekstu ze zdjęcia"
    else:
        mode = "analyze"
        operation_name = "Analiza zdjęcia"
    
    # Check operation cost and show warning if needed
    cost_warning = check_operation_cost(user_id, credit_cost, credits, operation_name, context)
    if cost_warning['require_confirmation'] and cost_warning['level'] in ['warning', 'critical']:
        # Show warning and ask for confirmation
        warning_message = create_header("Potwierdzenie kosztu", "warning")
        warning_message += cost_warning['message'] + "\n\nCzy chcesz kontynuować?"
        
        # Create confirmation buttons
        callback_data = f"confirm_photo_{mode}_{photo.file_id}"
        keyboard = [
            [
                InlineKeyboardButton("✅ Tak, kontynuuj", callback_data=callback_data),
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            warning_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Save photo info in context for later use
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
            
        context.chat_data['user_data'][user_id]['last_photo_id'] = photo.file_id
        context.chat_data['user_data'][user_id]['last_photo_mode'] = mode
        
        return
    
    # Proceed with analysis if no confirmation needed
    # Wyślij informację o rozpoczęciu analizy/tłumaczenia
    if mode == "translate":
        message = await update.message.reply_text(
            create_status_indicator('loading', "Tłumaczenie tekstu ze zdjęcia")
        )
    else:
        message = await update.message.reply_text(
            create_status_indicator('loading', "Analizowanie zdjęcia")
        )
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Store credits before the operation for reporting
    credits_before = credits
    
    # Pobierz zdjęcie
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Analizuj zdjęcie w odpowiednim trybie
    result = await analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg", mode=mode)
    
    # Odejmij kredyty
    deduct_user_credits(user_id, credit_cost, "Tłumaczenie tekstu ze zdjęcia" if mode == "translate" else "Analiza zdjęcia")
    
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
        "Tłumaczenie tekstu" if mode == "translate" else "Analiza zdjęcia", 
        credit_cost, 
        credits_before, 
        credits_after
    )
    result_message += f"\n\n{usage_report}"
    
    # Add a tip if appropriate
    if should_show_tip(user_id, context):
        tip = get_random_tip('document')
        result_message += f"\n\n💡 *Porada:* {tip}"
    
    # Wyślij analizę/tłumaczenie do użytkownika
    await message.edit_text(
        result_message,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź aktualny stan kredytów
    if credits_after < 5:
        low_credits_warning = create_header("Niski stan kredytów", "warning")
        low_credits_warning += f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota."
        
        # Add buttons to buy credits
        keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            low_credits_warning,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )