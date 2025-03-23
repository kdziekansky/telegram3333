# handlers/callback_handler.py
"""
Zmodyfikowany handler callbacków z aktualizacją do nowego systemu menu
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from utils.translations import get_text
from utils.user_utils import get_user_language, is_chat_initialized, mark_chat_initialized
from database.supabase_client import (
    get_active_conversation, create_new_conversation
)
from utils.menu_manager import update_menu_message, store_menu_state
from config import AVAILABLE_MODELS, DEFAULT_MODEL, CHAT_MODES, CREDIT_COSTS

async def handle_buy_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje przycisk zakupu kredytów"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Importuj funkcję buy_command
        from handlers.credit_handler import buy_command
        
        # Utwórz sztuczny obiekt update
        fake_update = type('obj', (object,), {
            'effective_user': query.from_user,
            'message': query.message,
            'effective_chat': query.message.chat
        })
        
        # Usuń oryginalną wiadomość z menu, aby nie powodować zamieszania
        await query.message.delete()
        
        # Wywołaj nowy interfejs zakupów (/buy)
        await buy_command(fake_update, context)
        
        return True
    except Exception as e:
        print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
        import traceback
        traceback.print_exc()
        return False

async def handle_unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wszystkie nieznane callbacki"""
    query = update.callback_query
    await query.answer("Ta funkcja jest w trakcie implementacji")
    
    # Logowanie nieznanego callbacka
    print(f"Nieobsłużony callback: {query.data}")
    
    # Informacja dla użytkownika
    try:
        message_text = f"Funkcja '{query.data}' jest w trakcie implementacji.\n\nWróć do menu głównego i spróbuj innej opcji."
        keyboard = [[InlineKeyboardButton("⬅️ Powrót do menu", callback_data="menu_back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Wykorzystanie centralnego systemu menu
        await update_menu_message(
            query,
            message_text,
            reply_markup
        )
        
        # Zapisz stan menu
        store_menu_state(context, query.from_user.id, 'unknown_callback')
        
        return True
    except Exception as e:
        print(f"Błąd przy edycji wiadomości: {e}")
        return False

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa zapytań zwrotnych - szybkie akcje"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodaj logger
    print(f"Otrzymano callback: {query.data} od użytkownika {user_id}")
    
    # Najpierw odpowiedz, aby usunąć oczekiwanie
    await query.answer()
    
    # Szybkie akcje 
    if query.data == "quick_new_chat":
        try:
            # Utwórz nową konwersację
            conversation = create_new_conversation(user_id)
            mark_chat_initialized(context, user_id)
            
            await query.answer(get_text("new_chat_created", language))
            
            # Zamknij menu, aby użytkownik mógł zacząć pisać
            await query.message.delete()
            
            # Determine current mode and cost
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
            base_message = "✅ Utworzono nową rozmowę. Możesz zacząć pisać! "
            model_info = f"Używasz modelu {model_name} za {credit_cost} kredyt(ów) za wiadomość"
            
            # Tylko jeden przycisk - wybór modelu
            keyboard = [
                [InlineKeyboardButton("🤖 Wybierz model czatu", callback_data="settings_model")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Wyślij komunikat potwierdzający
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=base_message + model_info,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            print(f"Błąd przy tworzeniu nowej rozmowy: {e}")
            import traceback
            traceback.print_exc()
            return False

    elif query.data == "quick_last_chat":
        try:
            # Pobierz aktywną konwersację
            conversation = get_active_conversation(user_id)
            
            if conversation:
                await query.answer(get_text("returning_to_last_chat", language, default="Powrót do ostatniej rozmowy"))
                
                # Zamknij menu
                await query.message.delete()
            else:
                await query.answer(get_text("no_active_chat", language, default="Brak aktywnej rozmowy"))
                
                # Utwórz nową konwersację
                create_new_conversation(user_id)
                
                # Zamknij menu
                await query.message.delete()
                
                # Wyślij komunikat
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=get_text("new_chat_created_message", language)
                )
            return True
        except Exception as e:
            print(f"Błąd przy obsłudze ostatniej rozmowy: {e}")
            import traceback
            traceback.print_exc()
            return False

    elif query.data == "quick_buy_credits":
        return await handle_buy_credits(update, context)
    
    # Jeśli doszliśmy tutaj, callback nie został obsłużony
    return await handle_unknown_callback(update, context)