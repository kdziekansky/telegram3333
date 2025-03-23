from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from utils.translations import get_text
from utils.user_utils import get_user_language
from config import BOT_NAME, CHAT_MODES, AVAILABLE_MODELS, CREDIT_COSTS
from utils.menu_manager import update_menu_message, store_menu_state, get_navigation_path
from utils.visual_styles import create_header, create_section
from utils.message_formatter_enhanced import enhance_credits_display, enhance_help_message

# Przenieś tu funkcje obsługujące poszczególne sekcje menu:
async def handle_chat_modes_section(update, context, navigation_path=""):
    """Obsługuje sekcję trybów czatu z ulepszoną prezentacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if navigation_path:
        message_text = f"*{navigation_path}*\n\n"
    
    # Add styled header for chat modes section
    message_text += create_header("Tryby Konwersacji", "chat")
    message_text += get_text("select_chat_mode", language)
    
    # Add visual explanation of cost indicators
    message_text += "\n\n" + create_section("Oznaczenia Kosztów", 
        "🟢 1 kredyt - tryby ekonomiczne\n🟠 2-3 kredytów - tryby standardowe\n🔴 5+ kredytów - tryby premium")
    
    # Customized keyboard with cost indicators
    keyboard = []
    for mode_id, mode_info in CHAT_MODES.items():
        # Pobierz przetłumaczoną nazwę trybu
        mode_name = get_text(f"chat_mode_{mode_id}", language, default=mode_info['name'])
        
        # Add cost indicator emoji based on credit cost
        if mode_info['credit_cost'] == 1:
            cost_indicator = "🟢"  # Green for economy options
        elif mode_info['credit_cost'] <= 3:
            cost_indicator = "🟠"  # Orange for standard options
        else:
            cost_indicator = "🔴"  # Red for expensive options
        
        # Add premium star for premium modes
        if mode_info['credit_cost'] >= 3 and "gpt-4" in mode_info.get('model', ''):
            premium_marker = "⭐ "
        else:
            premium_marker = ""
        
        # Create button with visual indicators
        keyboard.append([
            InlineKeyboardButton(
                f"{premium_marker}{mode_name} {cost_indicator} {mode_info['credit_cost']} kr.", 
                callback_data=f"mode_{mode_id}"
            )
        ])
    
    # Pasek szybkiego dostępu
    keyboard.append([
        InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
        InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
        InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
    ])
    
    # Dodaj przycisk powrotu w jednolitym miejscu
    keyboard.append([
        InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu_message(
        query, 
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'chat_modes')
    
    return result

async def handle_credits_section(update, context, navigation_path=""):
    """Obsługuje sekcję kredytów z ulepszoną wizualizacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if navigation_path:
        message_text = f"*{navigation_path}*\n\n"
    
    credits = get_user_credits(user_id)
    
    # Use enhanced credit display with status bar and visual indicators
    message_text += enhance_credits_display(credits, BOT_NAME)
    
    # Add a random tip about credits if appropriate
    if should_show_tip(user_id, context):
        tip = get_random_tip('credits')
        message_text += f"\n\n{section_divider('Porada')}\n💡 *Porada:* {tip}"
    
    # Check for low credits and add warning if needed
    low_credits_warning = get_low_credits_notification(credits)
    if low_credits_warning:
        message_text += f"\n\n{section_divider('Uwaga')}\n{low_credits_warning}"
    
    reply_markup = create_credits_menu_markup(language)
    
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'credits')
    
    return result

async def handle_settings_section(update, context, navigation_path=""):
    """Obsługuje sekcję ustawień"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if navigation_path:
        message_text = f"*{navigation_path}*\n\n"
    
    message_text += get_text("settings_options", language)
    reply_markup = create_settings_menu_markup(language)
    
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'settings')
    
    return result

async def handle_history_section(update, context, navigation_path=""):
    """Obsługuje sekcję historii"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if navigation_path:
        message_text = f"*{navigation_path}*\n\n"
    
    message_text += get_text("history_options", language) + "\n\n" + get_text("export_info", language, default="Aby wyeksportować konwersację, użyj komendy /export")
    reply_markup = create_history_menu_markup(language)
    
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'history')
    
    return result

async def handle_help_section(update, context, navigation_path=""):
    """Obsługuje sekcję pomocy z ulepszoną wizualizacją"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if navigation_path:
        message_text = f"*{navigation_path}*\n\n"
    
    # Get the base help text
    help_text = get_text("help_text", language)
    
    # Apply enhanced formatting
    message_text += enhance_help_message(help_text)
    
    # Add a command shortcuts section
    command_shortcuts = (
        "▪️ /start - Rozpocznij bota\n"
        "▪️ /menu - Otwórz menu główne\n"
        "▪️ /credits - Sprawdź kredyty\n"
        "▪️ /buy - Kup kredyty\n" 
        "▪️ /mode - Wybierz tryb czatu\n"
        "▪️ /image - Generuj obraz\n"
        "▪️ /help - Wyświetl pomoc\n"
        "▪️ /status - Sprawdź status\n"
    )
    
    message_text += f"\n\n{section_divider('Skróty Komend')}\n{command_shortcuts}"
    
    # Add a random tip if appropriate
    if should_show_tip(user_id, context):
        tip = get_random_tip()
        message_text += f"\n\n{section_divider('Porada Dnia')}\n💡 *Porada:* {tip}"
    
    keyboard = [
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'help')
    
    return result

async def handle_image_section(update, context, navigation_path=""):
    """Obsługuje sekcję generowania obrazów"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Dodajemy pasek nawigacyjny do tekstu, jeśli podano
    message_text = ""
    if navigation_path:
        message_text = f"*{navigation_path}*\n\n"
    
    message_text += get_text("image_usage", language)
    keyboard = [
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ],
        [InlineKeyboardButton("⬅️ " + get_text("back", language), callback_data="menu_back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    result = await update_menu_message(
        query,
        message_text,
        reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz stan menu
    store_menu_state(context, user_id, 'image')
    
    return result