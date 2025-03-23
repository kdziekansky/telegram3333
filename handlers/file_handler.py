# handlers/file_handler.py - skonwertowany
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CREDIT_COSTS
from utils.translations import get_text
from utils.openai_client import analyze_document, analyze_image
from utils.tips import get_random_tip, should_show_tip
from utils.visual_styles import create_header, create_section, create_status_indicator
from handlers.base_handler import BaseHandler
from database.supabase_client import check_active_subscription

class FileHandler(BaseHandler):
    """
    Handler do obsługi plików (dokumentów i zdjęć)
    """
    
    @staticmethod
    async def _analyze_document_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Faktyczna operacja analizy dokumentu - wydzielona do osobnej metody
        """
        user_id = update.effective_user.id
        document = update.message.document
        file_name = document.file_name
        
        # Pobierz plik
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Analizuj plik
        analysis = await analyze_document(file_bytes, file_name)
        
        # Zwróć wyniki analizy
        return {
            "analysis": analysis,
            "file_name": file_name
        }
    
    @staticmethod
    async def _analyze_photo_operation(update: Update, context: ContextTypes.DEFAULT_TYPE, mode="analyze"):
        """
        Faktyczna operacja analizy zdjęcia - wydzielona do osobnej metody
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            mode: Tryb analizy ("analyze" lub "translate")
            
        Returns:
            dict: Wyniki analizy
        """
        # Wybierz zdjęcie o najwyższej rozdzielczości
        photo = update.message.photo[-1]
        
        # Pobierz zdjęcie
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()
        
        # Analizuj zdjęcie w odpowiednim trybie
        result = await analyze_image(file_bytes, f"photo_{photo.file_unique_id}.jpg", mode=mode)
        
        # Zwróć wyniki analizy
        return {
            "result": result,
            "mode": mode,
            "photo_id": photo.file_id
        }
    
    @staticmethod
    async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Obsługa przesłanych dokumentów z ulepszoną prezentacją
        """
        user_id = update.effective_user.id
        language = FileHandler.get_user_language(context, user_id)
        document = update.message.document
        file_name = document.file_name
        
        # Sprawdź, czy użytkownik ma aktywną subskrypcję
        if not check_active_subscription(user_id):
            keyboard = [
                [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
                [InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await FileHandler.send_error(
                update,
                context,
                get_text("subscription_expired_message", language, default="Twoja subskrypcja wygasła lub nie masz wystarczającej liczby kredytów, aby wykonać tę operację. Kup pakiet kredytów, aby kontynuować."),
                show_back_button=False
            )
            return
        
        # Sprawdź rozmiar pliku (limit 25MB)
        if document.file_size > 25 * 1024 * 1024:
            file_size_mb = document.file_size / (1024 * 1024)
            error_message = get_text(
                "file_too_large", 
                language, 
                size=f"{file_size_mb:.1f}", 
                default=f"Maksymalny rozmiar pliku to 25MB. Twój plik ma {file_size_mb:.1f}MB. Spróbuj zmniejszyć rozmiar pliku lub podzielić go na mniejsze części."
            )
            
            await FileHandler.send_error(update, context, error_message)
            return
        
        # Sprawdź podpis, aby określić rodzaj operacji
        caption = update.message.caption or ""
        caption_lower = caption.lower()
        is_pdf = file_name.lower().endswith('.pdf')
        
        # Jeśli plik to PDF i użytkownik wspomina o tłumaczeniu, pokaż opcje
        if is_pdf and any(word in caption_lower for word in ["tłumacz", "przetłumacz", "translate", "переводить"]):
            options_message = (
                f"Wykryto dokument PDF: *{file_name}*\n\n"
                f"Wybierz co chcesz zrobić z tym dokumentem:"
            )
            
            # Pokaż koszty operacji
            options_message += "\n\n" + create_section("Koszt operacji", 
                f"▪️ Analiza dokumentu: *{CREDIT_COSTS['document']}* kredytów\n"
                f"▪️ Tłumaczenie dokumentu: *8* kredytów")
            
            # Dodaj poradę, jeśli potrzebna
            if should_show_tip(user_id, context):
                tip = get_random_tip('document')
                options_message += f"\n\n💡 *Porada:* {tip}"
            
            # Przyciski operacji
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
            
            await FileHandler.send_message(
                update,
                context,
                options_message,
                reply_markup=reply_markup,
                category="document"
            )
            
            # Zapisz informacje o dokumencie w kontekście
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
                
            context.chat_data['user_data'][user_id]['last_document_id'] = document.file_id
            context.chat_data['user_data'][user_id]['last_document_name'] = file_name
            
            return
        
        # Standardowa analiza dokumentu
        credit_cost = CREDIT_COSTS["document"]
        
        # Uruchom operację z obsługą kredytów
        result = await FileHandler.process_operation_with_credits(
            update,
            context,
            credit_cost,
            "Analiza dokumentu",
            FileHandler._analyze_document_operation
        )
        
        if not result:
            # Operacja przerwana lub błąd
            return
        
        # Przygotuj wiadomość wynikową
        file_name = result["file_name"]
        analysis = result["analysis"]
        
        # Skróć analizę, jeśli jest za długa
        analysis_excerpt = analysis[:3000]
        if len(analysis) > 3000:
            analysis_excerpt += "...\n\n(Analiza została skrócona ze względu na długość)"
        
        result_message = f"*Analiza dokumentu:* {file_name}\n\n{analysis_excerpt}"
        
        # Dodaj poradę, jeśli potrzebna
        if should_show_tip(user_id, context):
            tip = get_random_tip('document')
            result_message += f"\n\n💡 *Porada:* {tip}"
        
        # Wyślij analizę do użytkownika
        await FileHandler.send_message(
            update,
            context,
            result_message,
            category="document"
        )
    
    @staticmethod
    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Obsługa przesłanych zdjęć z ulepszoną prezentacją
        """
        user_id = update.effective_user.id
        language = FileHandler.get_user_language(context, user_id)
        
        # Sprawdź, czy użytkownik ma aktywną subskrypcję
        if not check_active_subscription(user_id):
            keyboard = [
                [InlineKeyboardButton("💳 " + get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
                [InlineKeyboardButton("⬅️ " + get_text("back", language, default="Powrót"), callback_data="menu_back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await FileHandler.send_error(
                update,
                context,
                get_text("subscription_expired_message", language, default="Twoja subskrypcja wygasła lub nie masz wystarczającej liczby kredytów, aby wykonać tę operację. Kup pakiet kredytów, aby kontynuować."),
                show_back_button=False
            )
            return
        
        # Wybierz zdjęcie o najwyższej rozdzielczości
        photo = update.message.photo[-1]
        
        # Określ koszt operacji
        credit_cost = CREDIT_COSTS["photo"]
        
        # Sprawdź podpis, aby określić rodzaj operacji
        caption = update.message.caption or ""
        
        # Jeśli nie ma podpisu, pokaż opcje
        if not caption:
            options_message = get_text("photo_options", language, default="Wykryto zdjęcie. Wybierz co chcesz zrobić z tym zdjęciem:")
            
            # Pokaż koszty operacji
            options_message += "\n\n" + create_section("Koszt operacji", 
                f"▪️ Analiza zdjęcia: *{CREDIT_COSTS['photo']}* kredytów\n"
                f"▪️ Tłumaczenie tekstu: *{CREDIT_COSTS['photo']}* kredytów")
            
            # Dodaj poradę, jeśli potrzebna
            if should_show_tip(user_id, context):
                tip = get_random_tip('document')
                options_message += f"\n\n💡 *Porada:* {tip}"
            
            # Przyciski operacji
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
            
            await FileHandler.send_message(
                update,
                context,
                options_message,
                reply_markup=reply_markup,
                category="image"
            )
            
            # Zapisz informacje o zdjęciu w kontekście
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
                
            context.chat_data['user_data'][user_id]['last_photo_id'] = photo.file_id
            
            return
        
        # Określ tryb analizy na podstawie podpisu
        caption_lower = caption.lower()
        
        # Sprawdź czy to tłumaczenie
        if any(word in caption_lower for word in ["tłumacz", "przetłumacz", "translate", "переводить"]):
            mode = "translate"
            operation_name = "Tłumaczenie tekstu ze zdjęcia"
        else:
            mode = "analyze"
            operation_name = "Analiza zdjęcia"
        
        # Stwórz funkcję lambda do wykonania odpowiedniej operacji z parametrem mode
        async def analyze_with_mode(update, context):
            return await FileHandler._analyze_photo_operation(update, context, mode)
        
        # Uruchom operację z obsługą kredytów
        result = await FileHandler.process_operation_with_credits(
            update,
            context,
            credit_cost,
            operation_name,
            analyze_with_mode
        )
        
        if not result:
            # Operacja przerwana lub błąd
            return
        
        # Przygotuj wiadomość wynikową
        analysis_result = result["result"]
        current_mode = result["mode"]
        
        if current_mode == "translate":
            category = "translation"
            title = "Tłumaczenie tekstu ze zdjęcia"
        else:
            category = "analysis"
            title = "Analiza zdjęcia"
        
        # Dodaj poradę, jeśli potrzebna
        tip_text = ""
        if should_show_tip(user_id, context):
            tip = get_random_tip('document')
            tip_text = f"\n\n💡 *Porada:* {tip}"
        
        # Wyślij analizę/tłumaczenie do użytkownika
        await FileHandler.send_message(
            update,
            context,
            f"{analysis_result}{tip_text}",
            category=category
        )

    @staticmethod
    async def handle_document_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Obsługuje potwierdzenie analizy dokumentu
        """
        query = update.callback_query
        user_id = query.from_user.id
        language = FileHandler.get_user_language(context, user_id)
        
        await query.answer()
        
        if query.data.startswith("confirm_doc_analysis_"):
            # Extract document_id from callback data
            document_id = query.data[20:]
            
            # Sprawdź dane dokumentu w kontekście
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
            credit_cost = CREDIT_COSTS["document"]
            
            # Pokaż informację o przetwarzaniu
            await query.edit_message_text(
                create_status_indicator('loading', "Analizowanie dokumentu") + "\n\n" +
                f"*Dokument:* {file_name}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Pobierz plik
            try:
                file = await context.bot.get_file(document_id)
                file_bytes = await file.download_as_bytearray()
                
                # Analizuj dokument
                analysis = await analyze_document(file_bytes, file_name)
                
                # Odejmij kredyty i stwórz raport
                credit_report = await FileHandler.deduct_credits(user_id, credit_cost, f"Analiza dokumentu: {file_name}", context)
                
                # Skróć analizę, jeśli jest za długa
                analysis_excerpt = analysis[:3000]
                if len(analysis) > 3000:
                    analysis_excerpt += "...\n\n(Analiza została skrócona ze względu na długość)"
                
                # Przygotuj rezultat
                result_message = create_header(f"Analiza dokumentu: {file_name}", "document")
                result_message += analysis_excerpt
                result_message += f"\n\n{credit_report['report']}"
                
                # Dodaj poradę, jeśli potrzebna
                if should_show_tip(user_id, context):
                    tip = get_random_tip('document')
                    result_message += f"\n\n💡 *Porada:* {tip}"
                
                # Wyślij rezultat
                await query.edit_message_text(
                    result_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Sprawdź stan kredytów
                await FileHandler.show_low_credits_warning(update, context, credit_report["credits_after"])
                
            except Exception as e:
                await query.edit_message_text(
                    create_header("Błąd analizy", "error") +
                    f"Wystąpił błąd podczas analizy dokumentu: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )