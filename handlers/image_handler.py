from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CREDIT_COSTS, DALL_E_MODEL
from utils.translations import get_text
from handlers.menu_handler import get_user_language
from database.credits_client import check_user_credits, deduct_user_credits, get_user_credits
from utils.openai_client import generate_image_dall_e
from utils.ui_elements import info_card, section_divider, feature_badge, progress_bar
from utils.visual_styles import style_message, create_header, create_section, create_status_indicator
from utils.tips import get_random_tip, should_show_tip
from utils.credit_warnings import check_operation_cost, format_credit_usage_report
from utils.menu_manager import update_menu_message  # Dodany import
import asyncio

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generuje obraz za pomocą DALL-E na podstawie opisu z ulepszoną prezentacją
    Użycie: /image [opis obrazu]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Get default quality and cost
    quality = "standard"  # domyślna jakość
    credit_cost = CREDIT_COSTS["image"][quality]
    
    # Get current credits
    credits = get_user_credits(user_id)
    
    # Check if the user has enough credits
    if not check_user_credits(user_id, credit_cost):
        # Show enhanced credit warning with visual indicators
        warning_message = create_header("Brak wystarczających kredytów", "warning")
        warning_message += (
            f"Nie masz wystarczającej liczby kredytów, aby wygenerować obraz.\n\n"
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
    
    # Check if prompt was provided
    if not context.args or len(' '.join(context.args)) < 3:
        # Show enhanced usage information with examples
        usage_message = create_header("Generowanie obrazów", "image")
        usage_message += (
            f"{get_text('image_usage', language, default='Użycie: /image [opis obrazu]')}\n\n"
            f"*Przykłady:*\n"
            f"▪️ /image zachód słońca nad górami z jeziorem\n"
            f"▪️ /image portret kobiety w stylu renesansowym\n"
            f"▪️ /image futurystyczne miasto nocą\n\n"
            f"*Wskazówki:*\n"
            f"▪️ Im bardziej szczegółowy opis, tym lepszy efekt\n"
            f"▪️ Możesz określić styl artystyczny (np. olejny, akwarela)\n"
            f"▪️ Dodaj informacje o oświetleniu, kolorach i kompozycji"
        )
        
        # Add a random tip about image generation
        if should_show_tip(user_id, context):
            tip = get_random_tip('image')
            usage_message += f"\n\n{section_divider('Porada')}\n💡 *Porada:* {tip}"
        
        await update.message.reply_text(
            usage_message,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    prompt = ' '.join(context.args)
    
    # Check operation cost and show warning if needed
    cost_warning = check_operation_cost(user_id, credit_cost, credits, "Generowanie obrazu", context)
    if cost_warning['require_confirmation'] and cost_warning['level'] in ['warning', 'critical']:
        # Show warning and ask for confirmation
        warning_message = create_header("Potwierdzenie kosztu", "warning")
        warning_message += cost_warning['message'] + "\n\nCzy chcesz kontynuować?"
        
        # Create confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Tak, generuj", callback_data=f"confirm_image_{prompt.replace(' ', '_')[:50]}"),
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            warning_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Powiadom użytkownika o rozpoczęciu generowania z wizualnym statusem
    message = await update.message.reply_text(
        create_status_indicator('loading', "Generowanie obrazu") + "\n\n" +
        f"*Prompt:* {prompt}\n" +
        f"*Koszt:* {credit_cost} kredytów"
    )

    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.UPLOAD_PHOTO)
    
    # Generuj obraz
    image_url = await generate_image_dall_e(prompt)
    
    # Store credits before the operation for reporting
    credits_before = credits
    
    # Odejmij kredyty
    deduct_user_credits(user_id, credit_cost, get_text("image_generation", language, default="Generowanie obrazu"))
    
    # Get credits after the operation
    credits_after = get_user_credits(user_id)
    
    if image_url:
        # Usuń wiadomość o ładowaniu
        await message.delete()
        
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
        
        # Add a random tip if appropriate
        if should_show_tip(user_id, context):
            tip = get_random_tip('image')
            caption += f"\n\n💡 *Porada:* {tip}"
        
        # Wyślij obraz
        await update.message.reply_photo(
            photo=image_url,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Aktualizuj wiadomość o błędzie
        error_message = create_header("Błąd generowania", "error")
        error_message += get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu. Spróbuj ponownie z innym opisem.")
        
        await message.edit_text(
            error_message,
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
        
        # Użycie centralnego systemu menu
        await update_menu_message(
            query,
            create_status_indicator('loading', "Generowanie obrazu") + "\n\n" +
            f"*Prompt:* {prompt}",
            None,  # Brak przycisków podczas ładowania
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
        
        # Generate image
        image_url = await generate_image_dall_e(prompt)
        
        # Store credits before the operation for reporting
        credits_before = credits
        
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
            # Użycie centralnego systemu menu
            await update_menu_message(
                query,
                create_header("Operacja anulowana", "info") +
                "Generowanie obrazu zostało anulowane.",
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]),
                parse_mode=ParseMode.MARKDOWN
            )