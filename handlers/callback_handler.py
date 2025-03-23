# handlers/callback_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from config import CREDIT_COSTS, DEFAULT_MODEL, CHAT_MODES
from utils.translations import get_text
from utils.menu_manager import update_menu_message, store_menu_state
from utils.user_utils import get_user_language, is_chat_initialized, mark_chat_initialized
from database.supabase_client import (
    get_active_conversation, save_message, get_conversation_history, increment_messages_used
)
from database.credits_client import get_user_credits, check_user_credits, deduct_user_credits
from utils.openai_client import analyze_image, analyze_document
from utils.visual_styles import create_header, create_status_indicator
from utils.credit_warnings import check_operation_cost, format_credit_usage_report
import datetime

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
        
    except Exception as e:
        print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
        import traceback
        traceback.print_exc()

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
    except Exception as e:
        print(f"Błąd przy edycji wiadomości: {e}")
        # W przypadku błędu, próbujemy wysłać nową wiadomość
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Funkcja '{query.data}' jest w trakcie implementacji.\n\nWróć do menu głównego i spróbuj innej opcji.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Powrót do menu", callback_data="menu_back_main")
                ]])
            )
        except Exception as e2:
            print(f"Drugi błąd przy wysyłaniu wiadomości: {e2}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługa zapytań zwrotnych (z przycisków)"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodaj logger
    print(f"Otrzymano callback: {query.data} od użytkownika {user_id}")
    
    # Najpierw odpowiedz, aby usunąć oczekiwanie
    await query.answer()
    
    # 10. Szybkie akcje
    if query.data == "quick_new_chat":
        try:
            # Utwórz nową konwersację
            from database.supabase_client import create_new_conversation
            conversation = create_new_conversation(user_id)
            mark_chat_initialized(context, user_id)
            
            await query.answer(get_text("new_chat_created", language))
            
            # Zamknij menu, aby użytkownik mógł zacząć pisać
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
            base_message = "✅ Utworzono nową rozmowę. Możesz zacząć pisać! "  # Ujednolicony komunikat
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

    # Obsługa wyboru modelu
    elif query.data == "settings_model":
        try:
            # Wyślij nową wiadomość z wyborem modelu
            message_text = "Wybierz model AI, którego chcesz używać:"
            
            # Tworzymy klawiaturę z dostępnymi modelami
            keyboard = []
            from config import AVAILABLE_MODELS, CREDIT_COSTS
            
            for model_id, model_name in AVAILABLE_MODELS.items():
                # Dodaj informację o koszcie kredytów
                credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"{model_name} ({credit_cost} kredytów/wiadomość)", 
                        callback_data=f"model_{model_id}"
                    )
                ])
            
            # Dodaj przycisk powrotu
            keyboard.append([
                InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_settings")
            ])
            
            # Wyślij nową wiadomość zamiast edytować
            message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Zapisz stan menu
            store_menu_state(context, user_id, 'model_selection', message.message_id)
            
            return True
        except Exception as e:
            print(f"Błąd przy obsłudze wyboru modelu: {e}")
            return False
        
    # Specjalna obsługa dla settings_language
    if query.data == "settings_language":
        from config import AVAILABLE_LANGUAGES
        keyboard = []
        for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
            keyboard.append([
                InlineKeyboardButton(
                    lang_name, 
                    callback_data=f"start_lang_{lang_code}"
                )
            ])
        
        # Dodaj przycisk powrotu
        keyboard.append([
            InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = get_text("settings_choose_language", language, default="Wybierz język:")
        
        # Wykorzystanie centralnego systemu menu
        await update_menu_message(
            query,
            message_text,
            reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Zapisz stan menu
        store_menu_state(context, user_id, 'language_selection')
        
        return True

    elif query.data == "quick_last_chat":
        try:
            # Pobierz aktywną konwersację
            from database.supabase_client import get_active_conversation
            conversation = get_active_conversation(user_id)
            
            if conversation:
                await query.answer(get_text("returning_to_last_chat", language, default="Powrót do ostatniej rozmowy"))
                
                # Zamknij menu
                await query.message.delete()
            else:
                await query.answer(get_text("no_active_chat", language, default="Brak aktywnej rozmowy"))
                
                # Utwórz nową konwersację
                from database.supabase_client import create_new_conversation
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

    elif query.data == "quick_buy_credits":
        try:
            # Przekieruj do zakupu kredytów
            from handlers.payment_handler import payment_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {'effective_user': query.from_user, 'message': query.message})
            await payment_command(fake_update, context)
            return True
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()
    
    elif query.data == "Kup":
        try:
            # Przekieruj do zakupu kredytów
            from handlers.credit_handler import buy_command
            
            # Utwórz sztuczny obiekt update
            fake_update = type('obj', (object,), {'effective_user': query.from_user, 'message': query.message})
            await buy_command(fake_update, context)
            return True
        except Exception as e:
            print(f"Błąd przy przekierowaniu do zakupu kredytów: {e}")
            import traceback
            traceback.print_exc()

    # Obsługa nowych callbacków dla zdjęć
    elif query.data == "analyze_photo" or query.data == "translate_photo":
        # Pobierz ID zdjęcia z kontekstu
        if 'user_data' not in context.chat_data or user_id not in context.chat_data['user_data'] or 'last_photo_id' not in context.chat_data['user_data'][user_id]:
            await query.answer("Nie znaleziono zdjęcia. Wyślij je ponownie.")
            return
            
        photo_id = context.chat_data['user_data'][user_id]['last_photo_id']
        mode = "translate" if query.data == "translate_photo" else "analyze"
        
        # Pobierz koszt
        credit_cost = CREDIT_COSTS["photo"]
        if not check_user_credits(user_id, credit_cost):
            await query.answer(get_text("subscription_expired", language))
            return
        
        # Informuj o rozpoczęciu analizy
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text("translating_image" if mode == "translate" else "analyzing_photo", language)
        )
        
        try:
            # Pobierz zdjęcie
            file = await context.bot.get_file(photo_id)
            file_bytes = await file.download_as_bytearray()
            
            # Analizuj zdjęcie
            result = await analyze_image(file_bytes, f"photo_{photo_id}.jpg", mode=mode)
            
            # Odejmij kredyty
            description = "Tłumaczenie tekstu ze zdjęcia" if mode == "translate" else "Analiza zdjęcia"
            deduct_user_credits(user_id, credit_cost, description)
            
            # Wyślij wynik
            header = "*Tłumaczenie tekstu ze zdjęcia:*\n\n" if mode == "translate" else "*Analiza zdjęcia:*\n\n"
            await message.edit_text(
                f"{header}{result}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Błąd przy analizie zdjęcia: {e}")
            await message.edit_text("Wystąpił błąd podczas analizy zdjęcia. Spróbuj ponownie.")

    elif query.data == "analyze_document" or query.data == "translate_document":
        # Pobierz ID dokumentu z kontekstu
        if ('user_data' not in context.chat_data or 
            user_id not in context.chat_data['user_data'] or 
            'last_document_id' not in context.chat_data['user_data'][user_id]):
            await query.answer("Nie znaleziono dokumentu. Wyślij go ponownie.")
            return
            
        document_id = context.chat_data['user_data'][user_id]['last_document_id']
        file_name = context.chat_data['user_data'][user_id].get('last_document_name', 'dokument')
        
        # Sprawdź czy to jest prośba o tłumaczenie PDF
        if query.data == "translate_document" and file_name.lower().endswith('.pdf'):
            # Zasymuluj aktualizację z oryginalnym plikiem PDF
            class MockDocument:
                def __init__(self, file_id, file_name):
                    self.file_id = file_id
                    self.file_name = file_name
            
            class MockMessage:
                def __init__(self, chat_id, document):
                    self.chat_id = chat_id
                    self.document = document
                    self.chat = type('obj', (object,), {'id': chat_id, 'send_action': lambda action: None})
                    
                async def reply_text(self, text):
                    return await context.bot.send_message(chat_id=self.chat_id, text=text)
            
            # Utwórz aktualizację z dokumentem
            mock_document = MockDocument(document_id, file_name)
            update.message = MockMessage(query.message.chat_id, mock_document)
            
            # Wywołaj handler PDF
            from handlers.pdf_handler import handle_pdf_translation
            await handle_pdf_translation(update, context)
            return
        
        # Obsługa standardowej analizy dokumentu
        # Pobierz koszt
        credit_cost = CREDIT_COSTS["document"]
        if not check_user_credits(user_id, credit_cost):
            await query.answer(get_text("subscription_expired", language))
            return
        
        # Informuj o rozpoczęciu analizy
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text("analyzing_file", language)
        )
        
        try:
            # Pobierz dokument
            file = await context.bot.get_file(document_id)
            file_bytes = await file.download_as_bytearray()
            
            # Analizuj dokument
            result = await analyze_document(file_bytes, file_name)
            
            # Odejmij kredyty
            deduct_user_credits(user_id, credit_cost, f"Analiza dokumentu: {file_name}")
            
            # Wyślij wynik
            await message.edit_text(
                f"*{get_text('file_analysis', language)}:* {file_name}\n\n{result}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Błąd przy analizie dokumentu: {e}")
            await message.edit_text("Wystąpił błąd podczas analizy dokumentu. Spróbuj ponownie.")
    
     # Jeśli dotarliśmy tutaj, oznacza to, że callback nie został obsłużony
    print(f"Nieobsłużony callback: {query.data}")
    
    # Zamiast próbować edytować istniejącą wiadomość, po prostu wysyłamy nową
    try:
        keyboard = [[InlineKeyboardButton("⬅️ Menu główne", callback_data="menu_back_main")]]
        
        # Wyślij nową wiadomość zamiast edytować istniejącą
        message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Nieznany przycisk '{query.data}'. Spróbuj ponownie później.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Zapisz stan menu dla nowej wiadomości
        store_menu_state(context, user_id, 'unknown_callback', message.message_id)
        
        # Spróbujmy odpowiedzieć na callback, aby usunąć oczekiwanie
        try:
            await query.answer("Funkcja w przygotowaniu")
        except:
            pass
            
        return True
    except Exception as e:
        print(f"Błąd przy obsłudze nieobsłużonego callbacku: {e}")
        return False