from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from utils.translations import get_text
from utils.pdf_translator import translate_pdf_first_paragraph
from database.credits_client import check_user_credits, deduct_user_credits, get_user_credits
from handlers.menu_handler import get_user_language

async def handle_pdf_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje tłumaczenie pierwszego akapitu z pliku PDF
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
    credit_cost = 8  # Ustalamy koszt operacji tłumaczenia PDF na 8 kredytów
    if not check_user_credits(user_id, credit_cost):
        await update.message.reply_text(get_text("subscription_expired", language))
        return
    
    # Sprawdź, czy wiadomość zawiera plik PDF
    if not update.message.document or not update.message.document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text(get_text("not_pdf_file", language, default="Plik nie jest w formacie PDF."))
        return
    
    document = update.message.document
    file_name = document.file_name
    
    # Sprawdź rozmiar pliku (limit 25MB)
    if document.file_size > 25 * 1024 * 1024:
        await update.message.reply_text(get_text("file_too_large", language))
        return
    
    # Wyślij informację o rozpoczęciu tłumaczenia
    status_message = await update.message.reply_text(get_text("translating_pdf", language))
    
    # Wyślij informację o aktywności bota
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Pobierz plik
    file = await context.bot.get_file(document.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Przetłumacz pierwszy akapit
    result = await translate_pdf_first_paragraph(file_bytes)
    
    # Odejmij kredyty
    deduct_user_credits(user_id, credit_cost, f"Tłumaczenie pliku PDF: {file_name}")
    
    # Przygotuj odpowiedź
    if result["success"]:
        response = f"*{get_text('pdf_translation_result', language)}*\n\n"
        response += f"*{get_text('original_text', language)}:*\n{result['original_text']}\n\n"
        response += f"*{get_text('translated_text', language)}:*\n{result['translated_text']}"
    else:
        response = f"*{get_text('pdf_translation_error', language)}*\n\n{result['error']}"
    
    # Wyślij wynik tłumaczenia
    await status_message.edit_text(
        text=response,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Sprawdź aktualny stan kredytów
    credits = get_user_credits(user_id)
    if credits < 5:
        await update.message.reply_text(
            f"*{get_text('low_credits_warning', language)}* {get_text('low_credits_message', language, credits=credits)}",
            parse_mode=ParseMode.MARKDOWN
        )