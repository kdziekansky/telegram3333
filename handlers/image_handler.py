from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CREDIT_COSTS, DALL_E_MODEL
from utils.translations import get_text
from handlers.menu_handler import get_user_language
from database.credits_client import check_user_credits, deduct_user_credits, get_user_credits
from utils.openai_client import generate_image_dall_e
from utils.visual_styles import create_header, create_status_indicator
from utils.credit_warnings import check_operation_cost, format_credit_usage_report
from utils.tips import get_random_tip, should_show_tip
from utils.menu import update_menu

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generuje obraz za pomocą DALL-E na podstawie opisu"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    quality = "standard"
    credit_cost = CREDIT_COSTS["image"][quality]
    credits = get_user_credits(user_id)
    
    if not check_user_credits(user_id, credit_cost):
        warning_message = create_header("Brak wystarczających kredytów", "warning") + \
            f"Nie masz wystarczającej liczby kredytów.\n\n" + \
            f"▪️ Koszt operacji: *{credit_cost}* kredytów\n" + \
            f"▪️ Twój stan kredytów: *{credits}* kredytów\n\n" + \
            f"Potrzebujesz jeszcze *{credit_cost - credits}* kredytów."
        
        keyboard = [
            [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
            [InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")]
        ]
        
        await update.message.reply_text(warning_message, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    if not context.args or len(' '.join(context.args)) < 3:
        usage_message = create_header("Generowanie obrazów", "image") + \
            f"{get_text('image_usage', language, default='Użycie: /image [opis obrazu]')}\n\n" + \
            f"*Przykłady:*\n" + \
            f"▪️ /image zachód słońca nad górami z jeziorem\n" + \
            f"▪️ /image portret kobiety w stylu renesansowym\n" + \
            f"▪️ /image futurystyczne miasto nocą\n\n" + \
            f"*Wskazówki:*\n" + \
            f"▪️ Im bardziej szczegółowy opis, tym lepszy efekt\n" + \
            f"▪️ Możesz określić styl artystyczny (np. olejny, akwarela)\n" + \
            f"▪️ Dodaj informacje o oświetleniu, kolorach i kompozycji"
        
        if should_show_tip(user_id, context):
            tip = get_random_tip('image')
            usage_message += f"\n\n💡 *Porada:* {tip}"
        
        await update.message.reply_text(usage_message, parse_mode=ParseMode.MARKDOWN)
        return
    
    prompt = ' '.join(context.args)
    
    cost_warning = check_operation_cost(user_id, credit_cost, credits, "Generowanie obrazu", context)
    if cost_warning['require_confirmation'] and cost_warning['level'] in ['warning', 'critical']:
        warning_message = create_header("Potwierdzenie kosztu", "warning") + \
            cost_warning['message'] + "\n\nCzy chcesz kontynuować?"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Tak, generuj", callback_data=f"confirm_image_{prompt.replace(' ', '_')[:50]}"),
                InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
            ]
        ]
        
        await update.message.reply_text(warning_message, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    message = await update.message.reply_text(
        create_status_indicator('loading', "Generowanie obrazu") + "\n\n" +
        f"*Prompt:* {prompt}\n" +
        f"*Koszt:* {credit_cost} kredytów"
    )

    await update.message.chat.send_action(action=ChatAction.UPLOAD_PHOTO)
    
    image_url = await generate_image_dall_e(prompt)
    
    credits_before = credits
    deduct_user_credits(user_id, credit_cost, get_text("image_generation", language, default="Generowanie obrazu"))
    credits_after = get_user_credits(user_id)
    
    if image_url:
        await message.delete()
        
        caption = create_header("Wygenerowany obraz", "image") + f"*Prompt:* {prompt}\n"
        
        usage_report = format_credit_usage_report("Generowanie obrazu", credit_cost, credits_before, credits_after)
        caption += f"\n{usage_report}"
        
        if should_show_tip(user_id, context):
            tip = get_random_tip('image')
            caption += f"\n\n💡 *Porada:* {tip}"
        
        await update.message.reply_photo(photo=image_url, caption=caption, parse_mode=ParseMode.MARKDOWN)
    else:
        error_message = create_header("Błąd generowania", "error") + \
            get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu.")
        
        await message.edit_text(error_message, parse_mode=ParseMode.MARKDOWN)
    
    if credits_after < 5:
        low_credits_warning = create_header("Niski stan kredytów", "warning") + \
            f"Pozostało Ci tylko *{credits_after}* kredytów. Rozważ zakup pakietu."
        
        keyboard = [[InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")]]
        await update.message.reply_text(low_credits_warning, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_image_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje potwierdzenie generowania obrazu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
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
        credits = get_user_credits(user_id)
        
        if not check_user_credits(user_id, credit_cost):
            await update_menu(
                query,
                create_header("Brak wystarczających kredytów", "error") +
                "W międzyczasie twój stan kredytów zmienił się i nie masz już wystarczającej liczby kredytów.",
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        credits_before = credits
        image_url = await generate_image_dall_e(prompt)
        deduct_user_credits(user_id, credit_cost, get_text("image_generation", language, default="Generowanie obrazu"))
        credits_after = get_user_credits(user_id)
        
        if image_url:
            caption = create_header("Wygenerowany obraz", "image") + f"*Prompt:* {prompt}\n"
            usage_report = format_credit_usage_report("Generowanie obrazu", credit_cost, credits_before, credits_after)
            caption += f"\n{usage_report}"
            
            if should_show_tip(user_id, context):
                tip = get_random_tip('image')
                caption += f"\n\n💡 *Porada:* {tip}"
            
            await query.message.delete()
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, 
                                        caption=caption, parse_mode=ParseMode.MARKDOWN)
        else:
            await update_menu(
                query,
                create_header("Błąd generowania", "error") +
                get_text("image_generation_error", language, default="Przepraszam, wystąpił błąd podczas generowania obrazu."),
                InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]]),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif query.data == "cancel_operation":
        await update_menu(
            query,
            create_header("Operacja anulowana", "info") +
            "Generowanie obrazu zostało anulowane.",
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]),
            parse_mode=ParseMode.MARKDOWN
        )