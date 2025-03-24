# handlers/menu_handler.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHAT_MODES, AVAILABLE_LANGUAGES, AVAILABLE_MODELS, BOT_NAME, CREDIT_COSTS
from utils.translations import get_text
from utils.user_utils import get_user_language, mark_chat_initialized
from database.supabase_client import update_user_language, create_new_conversation
from utils.menu import update_menu, store_menu_state, get_navigation_path
from database.credits_client import get_user_credits

logger = logging.getLogger(__name__)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu with inline buttons"""
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
            InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
        ],
        [
            InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
            InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
        ],
        [
            InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
            InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'main', message.message_id)

async def _create_section_menu(query, context, section_name, text_key, buttons, quick_access=True):
    """Reusable function to create section menus with consistent styling and navigation"""
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    nav_path = get_navigation_path(section_name, language)
    message_text = f"*{nav_path}*\n\n{get_text(text_key, language)}"
    
    # Add quick access buttons if requested
    if quick_access:
        buttons.append([
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ])
    
    # Always add back button
    buttons.append([InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, section_name)
    return result

async def handle_chat_modes_section(update, context, navigation_path=""):
    """Chat modes section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    buttons = []
    for mode_id, mode_info in CHAT_MODES.items():
        mode_name = get_text(f"chat_mode_{mode_id}", language, default=mode_info['name'])
        
        # Add cost indicators
        cost_indicator = "🟢" if mode_info['credit_cost'] == 1 else "🟠" if mode_info['credit_cost'] <= 3 else "🔴"
        premium_marker = "⭐ " if mode_info['credit_cost'] >= 3 else ""
        
        buttons.append([
            InlineKeyboardButton(
                f"{premium_marker}{mode_name} {cost_indicator} {mode_info['credit_cost']} kr.", 
                callback_data=f"mode_{mode_id}"
            )
        ])
    
    return await _create_section_menu(
        query, context, 'chat_modes', "select_chat_mode", buttons
    )

async def handle_credits_section(update, context, navigation_path=""):
    """Credits section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Usuwamy await
    credits = get_user_credits(user_id)
    
    message_text = f"*{navigation_path or get_navigation_path('credits', language)}*\n\n"
    message_text += f"*Stan kredytów*\n\nDostępne kredyty: *{credits}*\n\n*Koszty operacji:*\n"
    message_text += f"▪️ Wiadomość standardowa (GPT-3.5): 1 kredyt\n"
    message_text += f"▪️ Wiadomość premium (GPT-4o): 3 kredyty\n"
    message_text += f"▪️ Wiadomość ekspercka (GPT-4): 5 kredytów\n"
    message_text += f"▪️ Generowanie obrazu: 10-15 kredytów\n"
    message_text += f"▪️ Analiza dokumentu: 5 kredytów\n"
    message_text += f"▪️ Analiza zdjęcia: 8 kredytów\n\n"
    
    buttons = [
        [InlineKeyboardButton("💳 Kup kredyty", callback_data="menu_credits_buy")],
        [
            InlineKeyboardButton("💰 Metody płatności", callback_data="payment_command"),
            InlineKeyboardButton("🔄 Subskrypcje", callback_data="subscription_command")
        ],
        [InlineKeyboardButton("📜 Historia transakcji", callback_data="transactions_command")],
        # Quick access buttons
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language), callback_data="quick_last_chat")
        ],
        [InlineKeyboardButton("⬅️ Powrót", callback_data="menu_back_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'credits')
    return result

async def handle_history_section(update, context, navigation_path=""):
    """History section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    buttons = [
        [InlineKeyboardButton(get_text("new_chat", language), callback_data="history_new")],
        [InlineKeyboardButton(get_text("view_history", language), callback_data="history_view")],
        [InlineKeyboardButton(get_text("delete_history", language), callback_data="history_delete")]
    ]
    
    return await _create_section_menu(
        query, context, 'history', 
        "history_options", buttons
    )

async def handle_settings_section(update, context, navigation_path=""):
    """Settings section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Link do zdjęcia bannera
    banner_url = "https://i.imgur.com/YPubLDE.png?v-1123"
    
    nav_path = get_navigation_path('settings', language)
    message_text = f"*{nav_path}*\n\n{get_text('settings_options', language)}"
    
    buttons = [
        [InlineKeyboardButton(get_text("settings_model", language), callback_data="settings_model")],
        [InlineKeyboardButton(get_text("settings_language", language), callback_data="settings_language")],
        [InlineKeyboardButton(get_text("settings_name", language), callback_data="settings_name")]
    ]
    
    # Dodaj przyciski szybkiego dostępu
    buttons.append([
        InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
    ])
    
    # Dodaj przycisk powrotu
    buttons.append([InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    try:
        # Usuń poprzednią wiadomość
        await query.message.delete()
        
        # Wyślij nową wiadomość ze zdjęciem
        message = await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=banner_url,
            caption=message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Zapisz stan menu
        store_menu_state(context, user_id, 'settings', message.message_id)
        return True
    except Exception as e:
        logger.error(f"Błąd przy wyświetlaniu menu ustawień: {e}")
        # Alternatywna metoda, jeśli wysłanie zdjęcia się nie powiedzie
        try:
            result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
            store_menu_state(context, user_id, 'settings')
            return result
        except Exception as e2:
            logger.error(f"Drugi błąd przy wyświetlaniu menu ustawień: {e2}")
            return False

async def handle_image_section(update, context, navigation_path=""):
    """Image generation section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    text_key = "image_usage"
    message_text = f"*{navigation_path or get_navigation_path('image', language)}*\n\n"
    message_text += get_text(text_key, language, default="Aby wygenerować obraz, użyj komendy /image [opis obrazu]")
    
    # Add examples and tips
    message_text += "\n\n*Przykłady:*\n"
    message_text += "▪️ /image zachód słońca nad górami z jeziorem\n"
    message_text += "▪️ /image portret kobiety w stylu renesansowym\n"
    message_text += "▪️ /image futurystyczne miasto nocą\n\n"
    message_text += "*Wskazówki:*\n"
    message_text += "▪️ Im bardziej szczegółowy opis, tym lepszy efekt\n"
    message_text += "▪️ Możesz określić styl artystyczny (np. olejny, akwarela)\n"
    message_text += "▪️ Dodaj informacje o oświetleniu, kolorach i kompozycji"
    
    buttons = [[
        InlineKeyboardButton("🆕 " + get_text("new_chat", language), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language), callback_data="quick_buy_credits")
    ], [
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'image')
    return result

async def handle_back_to_main(update, context):
    """Back to main menu handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Link do zdjęcia bannera
    banner_url = "https://i.imgur.com/YPubLDE.png?v-1123"
    
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    keyboard = [
        [
            InlineKeyboardButton(get_text("menu_chat_mode", language), callback_data="menu_section_chat_modes"),
            InlineKeyboardButton(get_text("image_generate", language), callback_data="menu_image_generate")
        ],
        [
            InlineKeyboardButton(get_text("menu_credits", language), callback_data="menu_section_credits"),
            InlineKeyboardButton(get_text("menu_dialog_history", language), callback_data="menu_section_history")
        ],
        [
            InlineKeyboardButton(get_text("menu_settings", language), callback_data="menu_section_settings"),
            InlineKeyboardButton(get_text("menu_help", language), callback_data="menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Zamiast usuwać wiadomość, sprawdzamy czy to wiadomość z obrazkiem
        if hasattr(query.message, 'photo') and query.message.photo:
            # Dla wiadomości z obrazkiem - aktualizujemy podpis i przyciski
            await query.message.edit_caption(
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Dla zwykłych wiadomości - wysyłamy nowe zdjęcie, ale nie usuwamy starej wiadomości
            message = await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=banner_url,
                caption=welcome_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Zapisz stan menu
            store_menu_state(context, user_id, 'main', message.message_id)
        
        return True
    except Exception as e:
        logger.error(f"Error returning to main menu: {e}")
        
        # Alternatywna metoda - próba standardowej aktualizacji tekstu
        try:
            result = await update_menu(query, welcome_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
            store_menu_state(context, user_id, 'main')
            return result
        except Exception as e2:
            logger.error(f"Second error when returning to main menu: {e2}")
            
            # Ostateczna próba - wysłanie nowej wiadomości tekstowej
            try:
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                store_menu_state(context, user_id, 'main', message.message_id)
                return True
            except Exception as e3:
                logger.error(f"Third error when returning to main menu: {e3}")
                return False

async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Model selection handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_navigation_path('settings', language)} > {get_text('settings_choose_model', language)}*\n\n"
    message_text += get_text("settings_choose_model", language, default="Wybierz model AI:")
    
    buttons = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        buttons.append([
            InlineKeyboardButton(
                f"{model_name} ({credit_cost} {get_text('credits_per_message', language)})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'model_selection')
    return result

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Language selection handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    language_selection_text = get_text("settings_choose_language", language, default="Wybierz język interfejsu:")
    
    message_text = f"*{get_navigation_path('settings', language)} > {get_text('language_selection_title', language, default='Wybór języka')}*\n\n"
    message_text += language_selection_text
    
    buttons = []
    for lang_code, lang_name in AVAILABLE_LANGUAGES.items():
        buttons.append([InlineKeyboardButton(lang_name, callback_data=f"start_lang_{lang_code}")])
    
    buttons.append([InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    result = await update_menu(query, message_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
    store_menu_state(context, user_id, 'language_selection')
    return result

async def handle_help_section(update, context):
    """Help section handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Przyciski dla sekcji pomocy
    buttons = [
        [InlineKeyboardButton(get_text("commands_list", language, default="Lista komend"), callback_data="help_commands")],
        [InlineKeyboardButton("💰 " + get_text("user_credits", language, default="Kredyty"), callback_data="menu_section_credits")],
        [InlineKeyboardButton(get_text("contact_support", language, default="Kontakt"), callback_data="help_contact")]
    ]
    
    return await _create_section_menu(
        query, context, 'help', 
        "help_options", buttons
    )

async def handle_help_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje callbacki związane z sekcją pomocy"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "help_commands":
        # Lista komend
        commands_text = get_text("help_commands_list", language, default="""
*Lista dostępnych komend:*

- /start - Rozpocznij korzystanie z bota
- /credits - Sprawdź stan kredytów
- /buy - Kup pakiet kredytów
- /status - Sprawdź status konta
- /newchat - Rozpocznij nową konwersację
- /mode - Wybierz tryb czatu
- /models - Wybierz model AI
- /image [opis] - Wygeneruj obraz
- /export - Eksportuj konwersację do PDF
- /theme - Zarządzaj tematami konwersacji
- /remind [czas] [treść] - Ustaw przypomnienie
- /code [kod] - Aktywuj kod promocyjny
- /creditstats - Analiza wykorzystania kredytów
- /restart - Zrestartuj informacje o bocie
        """)
        
        keyboard = [[InlineKeyboardButton(get_text("back", language, default="⬅️ Powrót"), callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(query, commands_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        return True
        
    elif query.data == "help_credits":
        # Informacje o kredytach
        credits = get_user_credits(user_id)
        
        credits_text = get_text("help_credits_info", language, credits=credits, default=f"""
*Informacje o systemie kredytów:*

- Aktualna liczba kredytów: *{credits}*
- Kredyty są używane do wszystkich operacji w bocie

*Koszty operacji:*
- Wiadomość standardowa (GPT-3.5): 1 kredyt
- Wiadomość premium (GPT-4o): 3 kredyty
- Wiadomość ekspercka (GPT-4): 5 kredytów
- Generowanie obrazu: 10-15 kredytów
- Analiza dokumentu: 5 kredytów
- Analiza zdjęcia: 8 kredytów

Użyj /buy aby dokupić kredyty lub /creditstats aby sprawdzić statystyki wykorzystania.
        """)
        
        keyboard = [
            [InlineKeyboardButton(get_text("buy_credits_btn", language, default="💳 Kup kredyty"), callback_data="menu_credits_buy")],
            [InlineKeyboardButton(get_text("back", language, default="⬅️ Powrót"), callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(query, credits_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        return True
        
    elif query.data == "help_contact":
        # Informacje kontaktowe
        contact_text = get_text("help_contact_info", language, bot_name=BOT_NAME, default=f"""
*Kontakt i wsparcie:*

- Email: mypremium@noicyk.pro
- Telegram: @mypremiumsupportbot
- Czas odpowiedzi: do 24h w dni robocze

*Zgłaszanie błędów:*
Jeśli napotkasz problem, opisz dokładnie co się stało i w jakich okolicznościach.

*Sugestie:*
Chętnie przyjmujemy pomysły na nowe funkcje!
        """)
        
        keyboard = [[InlineKeyboardButton(get_text("back", language, default="⬅️ Powrót"), callback_data="menu_help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update_menu(query, contact_text, reply_markup, parse_mode=ParseMode.MARKDOWN)
        return True
        
    return False

async def handle_history_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """History-related callbacks handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "history_view":
        try:
            # Próba bezpośredniego dostępu do bazy danych
            from database.supabase_client import supabase
            
            # Najpierw spróbuj znaleźć aktywną konwersację
            try:
                response = supabase.table('conversations').select('*').eq('user_id', user_id).order('last_message_at', desc=True).limit(1).execute()
                conversations = response.data
                
                if not conversations:
                    message_text = get_text("history_no_conversation", language, default="Brak aktywnej konwersacji.")
                    await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
                    return True
                    
                conversation = conversations[0]
                conversation_id = conversation['id']
                
                # Pobierz wiadomości dla tej konwersacji
                messages_response = supabase.table('messages').select('*').eq('conversation_id', conversation_id).order('created_at').execute()
                messages = messages_response.data
                
                if not messages:
                    message_text = get_text("history_empty", language, default="Historia jest pusta.")
                    await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
                    return True
                
                # Teraz wyświetl historię
                message_text = f"*{get_text('history_title', language, default='Historia konwersacji')}*\n\n"
                
                # Pokazujemy tylko ostatnie 10 wiadomości
                last_messages = messages[-10:] if len(messages) > 10 else messages
                
                for i, msg in enumerate(last_messages):
                    sender = get_text("history_user", language) if msg.get('is_from_user') else get_text("history_bot", language)
                    content = msg.get('content', '')
                    if content and len(content) > 100:
                        content = content[:97] + "..."
                    content = content.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
                    message_text += f"{i+1}. *{sender}*: {content}\n\n"
                
                try:
                    await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]), parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    await update_menu(query, message_text.replace("*", ""), InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            except Exception as e:
                logger.error(f"Error accessing conversation data: {e}")
                await update_menu(query, f"Błąd dostępu do danych: {str(e)}", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
                
        except Exception as e:
            logger.error(f"Error in history_view: {e}")
            await update_menu(query, f"Wystąpił błąd: {str(e)}", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            
        return True
    
    elif query.data == "history_new":
        try:
            # Bezpośrednie tworzenie konwersacji
            from database.supabase_client import supabase
            from datetime import datetime
            import pytz
            
            now = datetime.now(pytz.UTC).isoformat()
            
            # Utwórz nową konwersację
            try:
                response = supabase.table('conversations').insert({
                    'user_id': user_id,
                    'created_at': now,
                    'last_message_at': now
                }).execute()
                
                # Oznacz czat jako zainicjowany
                mark_chat_initialized(context, user_id)
                
                message_text = "✅ Utworzono nową konwersację."
                await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            except Exception as e:
                logger.error(f"Error creating conversation: {e}")
                await update_menu(query, f"Błąd tworzenia konwersacji: {str(e)}", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            
        except Exception as e:
            logger.error(f"Error in history_new: {e}")
            await update_menu(query, "Wystąpił błąd podczas tworzenia nowej konwersacji.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            
        return True
    
    elif query.data == "history_delete":
        message_text = "Czy na pewno chcesz usunąć historię? Tej operacji nie można cofnąć."
        keyboard = [
            [InlineKeyboardButton("✅ Tak", callback_data="history_confirm_delete"), 
             InlineKeyboardButton("❌ Nie", callback_data="menu_section_history")]
        ]
        await update_menu(query, message_text, InlineKeyboardMarkup(keyboard))
        return True
    
    elif query.data == "history_confirm_delete":
        try:
            # Najpierw utwórz nową konwersację, a następnie usuń stare
            from database.supabase_client import supabase
            from datetime import datetime
            import pytz
            
            now = datetime.now(pytz.UTC).isoformat()
            
            # Utwórz nową konwersację
            try:
                supabase.table('conversations').insert({
                    'user_id': user_id,
                    'created_at': now,
                    'last_message_at': now
                }).execute()
                
                # Pobierz stare konwersacje
                response = supabase.table('conversations').select('id').eq('user_id', user_id).order('last_message_at', desc=True).limit(100).execute()
                
                if response.data and len(response.data) > 1:
                    # Pobierz wszystkie ID konwersacji poza najnowszą
                    conversation_ids = [conv['id'] for conv in response.data[1:]]
                    
                    # Usuń wiadomości ze starych konwersacji
                    for conv_id in conversation_ids:
                        supabase.table('messages').delete().eq('conversation_id', conv_id).execute()
                    
                    # Usuń stare konwersacje
                    for conv_id in conversation_ids:
                        supabase.table('conversations').delete().eq('id', conv_id).execute()
                
                message_text = "✅ Historia została pomyślnie usunięta."
                await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            except Exception as e:
                logger.error(f"Error deleting history: {e}")
                await update_menu(query, f"Błąd usuwania historii: {str(e)}", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            
        except Exception as e:
            logger.error(f"Error in history_confirm_delete: {e}")
            await update_menu(query, "Wystąpił błąd podczas usuwania historii.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_history")]]))
            
        return True
    
    return False

async def handle_settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings-related callbacks handler"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    if query.data == "settings_name":
        message_text = get_text("settings_change_name", language, default="Aby zmienić swoją nazwę, użyj komendy /setname [twoja_nazwa].")
        await update_menu(query, message_text, InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Powrót", callback_data="menu_section_settings")]]), parse_mode=ParseMode.MARKDOWN)
        return True
    
    return False