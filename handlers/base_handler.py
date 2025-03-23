# handlers/base_handler.py
"""
Bazowa klasa handlera do dziedziczenia przez wszystkie handlery
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from utils.translations import get_text
from utils.user_utils import get_user_language
from utils.visual_styles import create_header, create_section
from database.credits_client import get_user_credits, check_user_credits, deduct_user_credits
from utils.credit_warnings import check_operation_cost, format_credit_usage_report

logger = logging.getLogger(__name__)

class BaseHandler:
    """
    Bazowa klasa handlera zawierająca wspólne funkcjonalności dla wszystkich handlerów
    """
    
    @staticmethod
    def get_user_language(context, user_id):
        """
        Pobiera język użytkownika
        
        Args:
            context: Kontekst bota
            user_id: ID użytkownika
            
        Returns:
            str: Kod języka (pl, en, ru)
        """
        return get_user_language(context, user_id)
    
    @staticmethod
    async def check_credits(update, context, cost, operation_name, show_warning=True):
        """
        Sprawdza, czy użytkownik ma wystarczającą liczbę kredytów do wykonania operacji
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            cost: Koszt operacji w kredytach
            operation_name: Nazwa operacji
            show_warning: Czy wyświetlać ostrzeżenie o niskim stanie kredytów
            
        Returns:
            tuple: (bool, dict) - (Czy użytkownik ma wystarczającą liczbę kredytów, dane o ostrzeżeniu)
        """
        user_id = update.effective_user.id
        language = BaseHandler.get_user_language(context, user_id)
        credits = get_user_credits(user_id)
        
        # Sprawdź czy użytkownik ma wystarczającą liczbę kredytów
        if not check_user_credits(user_id, cost):
            # Utwórz klawiaturę z przyciskiem do zakupu kredytów
            keyboard = [
                [InlineKeyboardButton(get_text("buy_credits_btn", language), callback_data="menu_credits_buy")],
                [InlineKeyboardButton(get_text("back", language), callback_data="menu_back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Wyślij informację o braku kredytów
            await update.message.reply_text(
                create_header("Niewystarczające kredyty", "warning") +
                f"Nie masz wystarczającej liczby kredytów, aby wykonać tę operację.\n\n" +
                f"▪️ Koszt operacji: *{cost}* kredytów\n" +
                f"▪️ Twój stan kredytów: *{credits}* kredytów\n\n" +
                f"Potrzebujesz jeszcze *{cost - credits}* kredytów.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return False, None
        
        # Sprawdź ostrzeżenie o koszcie operacji
        if show_warning:
            warning = check_operation_cost(user_id, cost, credits, operation_name, context)
            if warning['require_confirmation'] and warning['level'] in ['warning', 'critical']:
                return True, warning
        
        return True, None
        
    @staticmethod
    async def deduct_credits(user_id, cost, operation_name, context=None):
        """
        Odejmuje kredyty i generuje raport
        
        Args:
            user_id: ID użytkownika
            cost: Koszt operacji
            operation_name: Nazwa operacji
            context: Kontekst bota (opcjonalnie)
            
        Returns:
            dict: Raport z operacji
        """
        # Pobierz stan kredytów przed operacją
        credits_before = get_user_credits(user_id)
        
        # Odejmij kredyty
        deduct_user_credits(user_id, cost, operation_name)
        
        # Pobierz stan kredytów po operacji
        credits_after = get_user_credits(user_id)
        
        # Utwórz raport
        language = "pl"
        if context:
            language = BaseHandler.get_user_language(context, user_id)
        
        report = format_credit_usage_report(operation_name, cost, credits_before, credits_after)
        
        return {
            "report": report,
            "credits_before": credits_before,
            "credits_after": credits_after,
            "cost": cost
        }
    
    @staticmethod
    async def show_low_credits_warning(update, context, credits):
        """
        Wyświetla ostrzeżenie o niskim stanie kredytów
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            credits: Aktualny stan kredytów
        """
        if credits < 5:
            user_id = update.effective_user.id
            language = BaseHandler.get_user_language(context, user_id)
            
            # Utwórz przycisk do zakupu kredytów
            keyboard = [[InlineKeyboardButton(get_text("buy_credits_btn_with_icon", language, default="🛒 Kup kredyty"), callback_data="menu_credits_buy")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Wyświetl ostrzeżenie
            await update.message.reply_text(
                create_header("Niski stan kredytów", "warning") +
                f"Pozostało Ci tylko *{credits}* kredytów. Rozważ zakup pakietu, aby kontynuować korzystanie z bota.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    @staticmethod
    async def send_message(update, context, text, reply_markup=None, parse_mode=ParseMode.MARKDOWN, category=None):
        """
        Wysyła wiadomość z formatowaniem i obsługą błędów
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            text: Tekst wiadomości
            reply_markup: Klawiatura przycisków (opcjonalnie)
            parse_mode: Tryb formatowania (opcjonalnie)
            category: Kategoria wiadomości dla stylizacji (opcjonalnie)
            
        Returns:
            telegram.Message: Wysłana wiadomość
        """
        try:
            # Dodaj stylizację jeśli podano kategorię
            if category:
                text = create_header(category, category) + text
            
            # Próba wysłania z formatowaniem
            return await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Błąd wysyłania wiadomości: {e}")
            
            # Próba wysłania bez formatowania
            try:
                # Usuń znaczniki formatowania
                clean_text = text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
                return await update.message.reply_text(
                    clean_text,
                    reply_markup=reply_markup
                )
            except Exception as e2:
                logger.error(f"Drugi błąd wysyłania wiadomości: {e2}")
                return None
    
    @staticmethod
    async def send_error(update, context, error_message, show_back_button=True):
        """
        Wysyła komunikat o błędzie
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            error_message: Treść komunikatu o błędzie
            show_back_button: Czy pokazywać przycisk powrotu do menu głównego
            
        Returns:
            telegram.Message: Wysłana wiadomość
        """
        user_id = update.effective_user.id
        language = BaseHandler.get_user_language(context, user_id)
        
        # Utwórz przycisk powrotu do menu głównego
        keyboard = []
        if show_back_button:
            keyboard.append([InlineKeyboardButton(get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Wyślij komunikat o błędzie
        return await BaseHandler.send_message(
            update, 
            context, 
            create_header("Błąd", "error") + error_message,
            reply_markup,
            category="error"
        )
    
    @staticmethod
    async def send_success(update, context, success_message, show_back_button=True):
        """
        Wysyła komunikat o sukcesie
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            success_message: Treść komunikatu o sukcesie
            show_back_button: Czy pokazywać przycisk powrotu do menu głównego
            
        Returns:
            telegram.Message: Wysłana wiadomość
        """
        user_id = update.effective_user.id
        language = BaseHandler.get_user_language(context, user_id)
        
        # Utwórz przycisk powrotu do menu głównego
        keyboard = []
        if show_back_button:
            keyboard.append([InlineKeyboardButton(get_text("back_to_main_menu", language, default="Powrót do menu głównego"), callback_data="menu_back_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Wyślij komunikat o sukcesie
        return await BaseHandler.send_message(
            update, 
            context, 
            create_header("Sukces", "success") + success_message,
            reply_markup,
            category="success"
        )
    
    @staticmethod
    async def show_waiting_message(update, context, operation_name=""):
        """
        Wyświetla komunikat o oczekiwaniu na zakończenie operacji
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            operation_name: Nazwa operacji (opcjonalnie)
            
        Returns:
            telegram.Message: Wysłana wiadomość
        """
        user_id = update.effective_user.id
        language = BaseHandler.get_user_language(context, user_id)
        
        # Wyślij odpowiednią akcję czatu (pisanie, wysyłanie zdjęcia, itp.)
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Utwórz komunikat o oczekiwaniu
        waiting_text = get_text("operation_in_progress", language, default="Operacja w toku, proszę czekać...")
        if operation_name:
            waiting_text = get_text("specific_operation_in_progress", language, operation=operation_name, default=f"Operacja '{operation_name}' w toku, proszę czekać...")
        
        # Wyświetl komunikat
        return await update.message.reply_text(
            create_header("Przetwarzanie", "info") + waiting_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    def create_menu_markup(buttons, language):
        """
        Tworzy klawiaturę przycisków menu
        
        Args:
            buttons (list): Lista konfiguracji przycisków w formacie:
                            [('text_key', 'callback_data'), ...]
                            lub
                            [('text_key', 'callback_data', 'prefix'), ...]
            language (str): Kod języka
            
        Returns:
            InlineKeyboardMarkup: Klawiatura przycisków
        """
        keyboard = []
        
        for row_buttons in buttons:
            row = []
            for button_config in row_buttons:
                if len(button_config) == 2:
                    text_key, callback_data = button_config
                    button_text = get_text(text_key, language, default=text_key)
                    row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
                elif len(button_config) == 3:
                    text_key, callback_data, prefix = button_config
                    button_text = f"{prefix} {get_text(text_key, language, default=text_key)}"
                    row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            keyboard.append(row)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    async def process_operation_with_credits(update, context, cost, operation_name, callback_function):
        """
        Wykonuje operację z obsługą kredytów, ostrzeżeń i błędów
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            cost: Koszt operacji w kredytach
            operation_name: Nazwa operacji
            callback_function: Funkcja do wykonania operacji (async)
            
        Returns:
            Wynik operacji lub None w przypadku błędu
        """
        user_id = update.effective_user.id
        
        # Sprawdź kredyty
        has_credits, warning = await BaseHandler.check_credits(update, context, cost, operation_name)
        if not has_credits:
            return None
        
        # Jeśli potrzebne potwierdzenie, zapisz w kontekście i zakończ
        if warning and warning['require_confirmation']:
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
            
            # Zapisz dane operacji dla późniejszego potwierdzenia
            context.chat_data['user_data'][user_id]['pending_operation'] = {
                'type': operation_name,
                'cost': cost,
                'callback_name': callback_function.__name__
            }
            
            # Wyświetl ostrzeżenie i przyciski potwierdzenia
            keyboard = [
                [
                    InlineKeyboardButton("✅ Tak, kontynuuj", callback_data=f"confirm_operation_{operation_name}"),
                    InlineKeyboardButton("❌ Anuluj", callback_data="cancel_operation")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                create_header("Potwierdzenie kosztu", "warning") +
                warning['message'] + "\n\nCzy chcesz kontynuować?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return None
        
        # Wyświetl komunikat o oczekiwaniu
        waiting_message = await BaseHandler.show_waiting_message(update, context, operation_name)
        
        try:
            # Wykonaj operację
            result = await callback_function(update, context)
            
            # Odejmij kredyty
            credit_report = await BaseHandler.deduct_credits(user_id, cost, operation_name, context)
            
            # Zaktualizuj lub usuń komunikat o oczekiwaniu
            await waiting_message.delete()
            
            # Sprawdź stan kredytów
            await BaseHandler.show_low_credits_warning(update, context, credit_report["credits_after"])
            
            return result
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania operacji {operation_name}: {e}")
            
            # Zaktualizuj komunikat o oczekiwaniu
            await waiting_message.edit_text(
                create_header("Błąd operacji", "error") +
                f"Wystąpił błąd podczas wykonywania operacji: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            return None