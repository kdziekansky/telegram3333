# handlers/chat_handler.py
"""
Moduł obsługujący wiadomości tekstowe od użytkownika
i komunikację z modelami AI
"""
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CHAT_MODES, DEFAULT_MODEL, MAX_CONTEXT_MESSAGES, CREDIT_COSTS
from database.supabase_client import (
    get_active_conversation, save_message, get_conversation_history, increment_messages_used
)
from utils.openai_client import chat_completion_stream, prepare_messages_from_history
from utils.translations import get_text
from utils.user_utils import is_chat_initialized
from utils.tips import get_contextual_tip, should_show_tip
from handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)

class ChatHandler(BaseHandler):
    """
    Handler do obsługi komunikacji tekstowej z modelami AI
    """
    
    @staticmethod
    async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Obsługa wiadomości tekstowych od użytkownika ze strumieniowaniem odpowiedzi
        """
        user_id = update.effective_user.id
        user_message = update.message.text
        language = ChatHandler.get_user_language(context, user_id)
        
        logger.info(f"Otrzymano wiadomość od użytkownika {user_id}")
        
        # Sprawdź, czy użytkownik zainicjował czat
        if not is_chat_initialized(context, user_id):
            # Wyświetl komunikat o konieczności zainicjowania czatu
            keyboard = [
                [InlineKeyboardButton(get_text("start_new_chat", language, default="Rozpocznij nowy czat"), callback_data="quick_new_chat")],
                [InlineKeyboardButton(get_text("select_mode", language, default="Wybierz tryb czatu"), callback_data="menu_section_chat_modes")],
                [InlineKeyboardButton(get_text("menu_help", language, default="Pomoc"), callback_data="menu_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await ChatHandler.send_message(
                update,
                context,
                get_text("no_active_chat_message", language, default="Aby rozpocząć używanie AI, najpierw utwórz nowy czat używając /newchat lub przycisku poniżej."),
                reply_markup,
                category="chat"
            )
            return
        
        # Określ tryb i koszt kredytów
        model_data = ChatHandler._get_model_and_cost(context, user_id)
        current_mode = model_data["mode"]
        credit_cost = model_data["cost"]
        model_to_use = model_data["model"]
        
        logger.info(f"Tryb: {current_mode}, model: {model_to_use}, koszt kredytów: {credit_cost}")
        
        # Sprawdź, czy użytkownik ma wystarczającą liczbę kredytów
        has_credits, warning = await ChatHandler.check_credits(update, context, credit_cost, "Wiadomość AI")
        if not has_credits:
            return
        
        # Jeśli potrzebne potwierdzenie kosztów, zapisz wiadomość w kontekście i zakończ
        if warning and warning['require_confirmation']:
            # Zapisz wiadomość w kontekście do późniejszego użycia
            if 'user_data' not in context.chat_data:
                context.chat_data['user_data'] = {}
            if user_id not in context.chat_data['user_data']:
                context.chat_data['user_data'][user_id] = {}
                
            context.chat_data['user_data'][user_id]['pending_message'] = user_message
            
            # Wyświetl ostrzeżenie i przyciski potwierdzenia
            keyboard = [
                [
                    InlineKeyboardButton("✅ Tak, wyślij", callback_data=f"confirm_message"),
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
            return
        
        # Pobierz lub utwórz aktywną konwersację
        try:
            conversation = get_active_conversation(user_id)
            conversation_id = conversation['id']
            logger.info(f"Aktywna konwersacja: {conversation_id}")
        except Exception as e:
            logger.error(f"Błąd przy pobieraniu konwersacji: {e}")
            await ChatHandler.send_error(
                update, 
                context, 
                get_text("conversation_error", language)
            )
            return
        
        # Zapisz wiadomość użytkownika do bazy danych
        try:
            save_message(conversation_id, user_id, user_message, is_from_user=True)
            logger.info("Wiadomość użytkownika zapisana w bazie")
        except Exception as e:
            logger.error(f"Błąd przy zapisie wiadomości użytkownika: {e}")
        
        # Wyślij informację, że bot pisze
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Pobierz historię konwersacji
        try:
            history = get_conversation_history(conversation_id, limit=MAX_CONTEXT_MESSAGES)
            logger.info(f"Pobrano historię konwersacji, liczba wiadomości: {len(history)}")
        except Exception as e:
            logger.error(f"Błąd przy pobieraniu historii: {e}")
            history = []
        
        # Przygotuj system prompt z wybranego trybu
        system_prompt = CHAT_MODES[current_mode]["prompt"]
        
        # Przygotuj wiadomości dla API OpenAI
        messages = prepare_messages_from_history(history, user_message, system_prompt)
        logger.info(f"Przygotowano {len(messages)} wiadomości dla API")
        
        # Wyślij początkową pustą wiadomość, którą będziemy aktualizować
        response_message = await update.message.reply_text(get_text("generating_response", language))
        
        # Generuj odpowiedź strumieniowo
        await ChatHandler._generate_streaming_response(
            update, 
            context, 
            response_message, 
            messages, 
            model_to_use, 
            current_mode, 
            credit_cost, 
            conversation_id
        )
    
    @staticmethod
    async def _generate_streaming_response(update, context, response_message, messages, model, mode, credit_cost, conversation_id):
        """
        Generuje odpowiedź strumieniowo i aktualizuje wiadomość
        
        Args:
            update: Obiekt Update
            context: Kontekst bota
            response_message: Wiadomość do aktualizacji
            messages: Wiadomości dla API
            model: Model AI do użycia
            mode: Tryb czatu
            credit_cost: Koszt operacji
            conversation_id: ID konwersacji
        """
        user_id = update.effective_user.id
        language = ChatHandler.get_user_language(context, user_id)
        
        # Pobierz kredyty przed operacją
        credits_before = await ChatHandler._get_user_credits(user_id)
        
        # Zainicjuj pełną odpowiedź
        full_response = ""
        buffer = ""
        last_update = datetime.datetime.now().timestamp()
        
        # Spróbuj wygenerować odpowiedź
        try:
            logger.info("Rozpoczynam generowanie odpowiedzi strumieniowej...")
            # Generuj odpowiedź strumieniowo
            async for chunk in chat_completion_stream(messages, model=model):
                full_response += chunk
                buffer += chunk
                
                # Aktualizuj wiadomość co 1 sekundę lub gdy bufor jest wystarczająco duży
                current_time = datetime.datetime.now().timestamp()
                if current_time - last_update >= 1.0 or len(buffer) > 100:
                    try:
                        # Dodaj migający kursor na końcu wiadomości
                        await response_message.edit_text(full_response + "▌", parse_mode=ParseMode.MARKDOWN)
                        buffer = ""
                        last_update = current_time
                    except Exception as e:
                        # Jeśli wystąpi błąd (np. wiadomość nie została zmieniona), kontynuuj
                        logger.warning(f"Błąd przy aktualizacji wiadomości: {e}")
            
            logger.info("Zakończono generowanie odpowiedzi")
            
            # Aktualizuj wiadomość z pełną odpowiedzią bez kursora
            try:
                await response_message.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                # Jeśli wystąpi błąd formatowania Markdown, wyślij bez formatowania
                logger.warning(f"Błąd formatowania Markdown: {e}")
                await response_message.edit_text(full_response)
            
            # Zapisz odpowiedź do bazy danych
            save_message(conversation_id, user_id, full_response, is_from_user=False, model_used=model)
            
            # Odejmij kredyty
            deduct_report = await ChatHandler.deduct_credits(
                user_id, 
                credit_cost, 
                get_text("message_model", language, model=model, default=f"Wiadomość ({model})"),
                context
            )
            credits_after = deduct_report["credits_after"]
            
            # Sprawdź aktualny stan kredytów
            await ChatHandler.show_low_credits_warning(update, context, credits_after)
            
            # Dodaj wskazówkę, jeśli odpowiednie
            tip = get_contextual_tip('chat', context, user_id)
            if tip:
                await update.message.reply_text(
                    f"💡 *Porada:* {tip}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Zwiększ licznik wykorzystanych wiadomości
            increment_messages_used(user_id)
            
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
            await response_message.edit_text(get_text("response_error", language, error=str(e)))
    
    @staticmethod
    def _get_model_and_cost(context, user_id):
        """
        Pobiera tryb czatu, model i koszt kredytów dla użytkownika
        
        Args:
            context: Kontekst bota
            user_id: ID użytkownika
            
        Returns:
            dict: Dane o trybie, modelu i koszcie
        """
        # Domyślne wartości
        current_mode = "no_mode"
        credit_cost = 1
        model_to_use = DEFAULT_MODEL
        
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            
            # Sprawdź tryb
            if 'current_mode' in user_data and user_data['current_mode'] in CHAT_MODES:
                current_mode = user_data['current_mode']
                credit_cost = CHAT_MODES[current_mode]["credit_cost"]
                model_to_use = CHAT_MODES[current_mode].get("model", DEFAULT_MODEL)
            
            # Sprawdź model (nadpisuje model z trybu)
            if 'current_model' in user_data and user_data['current_model'] in CREDIT_COSTS["message"]:
                model_to_use = user_data['current_model']
                credit_cost = CREDIT_COSTS["message"].get(model_to_use, CREDIT_COSTS["message"]["default"])
        
        return {
            "mode": current_mode,
            "model": model_to_use,
            "cost": credit_cost
        }
    
    @staticmethod
    async def _get_user_credits(user_id):
        """
        Pobiera kredyty użytkownika
        
        Args:
            user_id: ID użytkownika
            
        Returns:
            int: Liczba kredytów
        """
        from database.credits_client import get_user_credits
        return get_user_credits(user_id)


# Globalna funkcja exportowana dla zachowania wstecznej kompatybilności 
# z istniejącymi odwołaniami w main.py
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wrapper dla zachowania zgodności z istniejącymi odwołaniami
    """
    return await ChatHandler.message_handler(update, context)