# handlers/translate_handler.py
"""
Zoptymalizowany handler obsługi tłumaczeń z wykorzystaniem klasy bazowej
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from utils.translations import get_text
from utils.openai_client import chat_completion, analyze_image, analyze_document
from handlers.base_handler import BaseHandler
import re

logger = logging.getLogger(__name__)

class TranslateHandler(BaseHandler):
    """
    Handler do obsługi funkcji tłumaczenia tekstu, zdjęć i dokumentów
    """
    
    # Mapowanie kodów języków na ich nazwy
    LANGUAGE_NAMES = {
        "pl": "Polski",
        "en": "English",
        "ru": "Русский",
        "fr": "Français",
        "de": "Deutsch",
        "es": "Español",
        "it": "Italiano",
        "zh": "中文",
        "ja": "日本語",
        "ko": "한국어",
        "ar": "العربية",
        "pt": "Português"
    }
    
    @staticmethod
    async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Obsługa komendy /translate
        Instruuje użytkownika jak korzystać z funkcji tłumaczenia lub wykonuje tłumaczenie
        """
        user_id = update.effective_user.id
        language = TranslateHandler.get_user_language(context, user_id)
        
        # Sprawdź, czy komenda zawiera argumenty (tekst do tłumaczenia i docelowy język)
        if context.args and len(context.args) >= 2:
            # Format: /translate [język_docelowy] [tekst]
            # np. /translate en Witaj świecie!
            target_lang = context.args[0].lower()
            text_to_translate = ' '.join(context.args[1:])
            await TranslateHandler.translate_text(update, context, text_to_translate, target_lang)
            return
        
        # Sprawdź, czy wiadomość jest odpowiedzią na zdjęcie lub dokument
        if update.message.reply_to_message:
            # Obsługa odpowiedzi na wcześniejszą wiadomość
            replied_message = update.message.reply_to_message
            
            # Ustal docelowy język tłumaczenia z argumentów komendy
            target_lang = "en"  # Domyślnie angielski
            if context.args and len(context.args) > 0:
                target_lang = context.args[0].lower()
            
            if replied_message.photo:
                # Odpowiedź na zdjęcie - wykonaj tłumaczenie tekstu ze zdjęcia
                await TranslateHandler.translate_photo(update, context, replied_message.photo[-1], target_lang)
                return
            elif replied_message.document:
                # Odpowiedź na dokument - wykonaj tłumaczenie dokumentu
                await TranslateHandler.translate_document(update, context, replied_message.document, target_lang)
                return
            elif replied_message.text:
                # Odpowiedź na zwykłą wiadomość tekstową
                await TranslateHandler.translate_text(update, context, replied_message.text, target_lang)
                return
        
        # Jeśli nie ma odpowiedzi ani argumentów, wyświetl instrukcje
        instruction_text = get_text("translate_instruction", language, default=(
            "📄 **Tłumaczenie tekstu**\n\n"
            "Dostępne opcje:\n\n"
            "1. Wyślij zdjęcie z tekstem do tłumaczenia i dodaj /translate w opisie lub odpowiedz na zdjęcie komendą /translate\n\n"
            "2. Wyślij dokument i odpowiedz na niego komendą /translate\n\n"
            "3. Użyj komendy /translate [język_docelowy] [tekst]\n"
            "Na przykład: /translate en Witaj świecie!\n\n"
            "Dostępne języki docelowe: en (angielski), pl (polski), ru (rosyjski), fr (francuski), de (niemiecki), es (hiszpański), it (włoski), zh (chiński)"
        ))
        
        await TranslateHandler.send_message(update, context, instruction_text, category="translation")
    
    @staticmethod
    async def _translate_text_operation(update, context, text, target_lang):
        """
        Wykonuje operację tłumaczenia tekstu
        """
        language = TranslateHandler.get_user_language(context, update.effective_user.id)
        
        # Uniwersalny prompt niezależny od języka
        system_prompt = f"You are a professional translator. Translate the following text to {target_lang}. Preserve formatting. Only return the translation."
        
        # Przygotuj wiadomości dla API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        # Wykonaj tłumaczenie
        translation = await chat_completion(messages, model="gpt-3.5-turbo")
        
        # Przygotuj dane wynikowe
        source_lang_name = TranslateHandler.LANGUAGE_NAMES.get(language, language)
        target_lang_name = TranslateHandler.LANGUAGE_NAMES.get(target_lang, target_lang)
        
        return {
            "source_text": text,
            "translated_text": translation,
            "source_lang": source_lang_name,
            "target_lang": target_lang_name
        }
    
    @staticmethod
    async def translate_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text, target_lang="en"):
        """
        Tłumaczy podany tekst na określony język
        """
        user_id = update.effective_user.id
        language = TranslateHandler.get_user_language(context, user_id)
        
        # Koszt tłumaczenia tekstu
        credit_cost = 3
        
        # Wykonaj operację z obsługą kredytów
        result = await TranslateHandler.process_operation_with_credits(
            update,
            context,
            credit_cost,
            "Tłumaczenie tekstu",
            lambda u, c: TranslateHandler._translate_text_operation(u, c, text, target_lang)
        )
        
        if not result:
            return
        
        # Wyślij wynik tłumaczenia
        await TranslateHandler.send_message(
            update,
            context,
            f"*{get_text('translation_result', language, default='Wynik tłumaczenia')}* ({result['source_lang']} → {result['target_lang']})\n\n{result['translated_text']}",
            category="translation"
        )
    
    @staticmethod
    async def _translate_photo_operation(update, context, photo, target_lang):
        """
        Wykonuje operację tłumaczenia tekstu z zdjęcia
        """
        # Pobierz zdjęcie
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Tłumacz tekst ze zdjęcia w określonym kierunku
        result = await analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg", mode="translate", target_language=target_lang)
        
        return result
    
    @staticmethod
    async def translate_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, photo, target_lang="en"):
        """
        Tłumaczy tekst wykryty na zdjęciu
        """
        user_id = update.effective_user.id
        language = TranslateHandler.get_user_language(context, user_id)
        
        # Koszt tłumaczenia zdjęcia
        credit_cost = 8
        
        # Wykonaj operację z obsługą kredytów
        result = await TranslateHandler.process_operation_with_credits(
            update,
            context,
            credit_cost,
            "Tłumaczenie tekstu ze zdjęcia",
            lambda u, c: TranslateHandler._translate_photo_operation(u, c, photo, target_lang)
        )
        
        if not result:
            return
        
        # Wyślij wynik tłumaczenia
        await TranslateHandler.send_message(
            update,
            context,
            f"*{get_text('translation_result', language, default='Wynik tłumaczenia')}*\n\n{result}",
            category="translation"
        )
    
    @staticmethod
    async def _translate_document_operation(update, context, document, target_lang):
        """
        Wykonuje operację tłumaczenia dokumentu
        """
        file_name = document.file_name
        
        # Sprawdź rozmiar pliku (limit 25MB)
        if document.file_size > 25 * 1024 * 1024:
            raise ValueError(get_text("file_too_large", TranslateHandler.get_user_language(context, update.effective_user.id)))
        
        # Pobierz plik
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Tłumacz dokument
        result = await analyze_document(file_bytes, file_name, mode="translate", target_language=target_lang)
        
        return result
    
    @staticmethod
    async def translate_document(update: Update, context: ContextTypes.DEFAULT_TYPE, document, target_lang="en"):
        """
        Tłumaczy tekst z dokumentu
        """
        user_id = update.effective_user.id
        language = TranslateHandler.get_user_language(context, user_id)
        
        # Koszt tłumaczenia dokumentu
        credit_cost = 8
        
        # Wykonaj operację z obsługą kredytów
        result = await TranslateHandler.process_operation_with_credits(
            update,
            context,
            credit_cost,
            f"Tłumaczenie dokumentu na język {target_lang}",
            lambda u, c: TranslateHandler._translate_document_operation(u, c, document, target_lang)
        )
        
        if not result:
            return
        
        # Wyślij wynik tłumaczenia
        await TranslateHandler.send_message(
            update,
            context,
            f"*{get_text('translation_result', language, default='Wynik tłumaczenia')}*\n\n{result}",
            category="translation"
        )
    
    @staticmethod
    async def handle_operation_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Obsługuje potwierdzenie operacji tłumaczenia
        """
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()
        
        # Sprawdź, czy to potwierdzenie operacji tłumaczenia
        if not query.data.startswith("confirm_operation_"):
            return False
        
        # Usuń prefix, aby uzyskać nazwę operacji
        operation_type = query.data[18:]
        
        # Sprawdź, czy operacja jest zapisana w kontekście
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or 
            'pending_operation' not in context.chat_data['user_data'][user_id]):
            
            await query.edit_message_text(
                "Nie znaleziono oczekującej operacji tłumaczenia. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        
        pending_operation = context.chat_data['user_data'][user_id]['pending_operation']
        
        # Sprawdź, czy typ operacji się zgadza
        if pending_operation['type'] != operation_type:
            await query.edit_message_text(
                "Niezgodność typu operacji. Spróbuj ponownie.",
                parse_mode=ParseMode.MARKDOWN
            )
            return True
        
        # Usuń wiadomość z potwierdzeniem
        await query.message.delete()
        
        # Pokaż komunikat o oczekiwaniu
        waiting_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⏳ Trwa tłumaczenie...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # TODO: Tutaj należałoby wykonać faktyczną operację zgodnie z zapisanymi danymi
        # To jest uproszczona wersja - w pełnej implementacji byłoby wywołanie odpowiedniej funkcji
        # na podstawie danych zapisanych w pending_operation
        
        # Usuń oczekującą operację z kontekstu
        del context.chat_data['user_data'][user_id]['pending_operation']
        
        return True