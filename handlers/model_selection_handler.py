from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.translations import get_text
from utils.user_utils import get_user_language, mark_chat_initialized
from utils.menu_manager import update_menu_message, store_menu_state
from config import AVAILABLE_MODELS, CREDIT_COSTS, DEFAULT_MODEL

# Przenieś tu funkcje związane z wyborem modelu:
async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obsługuje wybór modelu AI z ulepszonym UI"""
    # Check if we're handling a callback query or a direct command
    if isinstance(update, Update) and update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        await query.answer()  # Acknowledge the callback query
    else:
        # This is a direct command or non-callback context
        user_id = update.effective_user.id

    language = get_user_language(context, user_id)
    
    print(f"Obsługa wyboru modelu dla użytkownika {user_id}")
    
    reply_markup = create_model_selection_markup(language)
    
    # If this is a callback query, update the message
    if isinstance(update, Update) and update.callback_query:
        result = await update_menu_message(
            update.callback_query, 
            get_text("settings_choose_model", language),
            reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # In any other case, just return the markup for use by caller
        return reply_markup
    
    return result

def create_model_selection_markup(language):
    """Tworzy klawiaturę dla wyboru modelu AI"""
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Dodaj informację o koszcie kredytów
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{model_name} ({credit_cost} {get_text('credits_per_message', language)})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language), callback_data="menu_section_settings")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla dostępne modele AI i pozwala użytkownikowi wybrać jeden z nich
    Użycie: /models
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    message_text = f"*{get_text('main_menu', language, default='Menu główne')} > {get_text('settings_choose_model', language, default='Wybór modelu')}*\n\n"
    message_text += get_text("settings_choose_model", language, default="Wybierz model AI, którego chcesz używać:")
    
    # Stwórz przyciski dla dostępnych modeli
    keyboard = []
    for model_id, model_name in AVAILABLE_MODELS.items():
        # Dodaj informację o koszcie kredytów
        credit_cost = CREDIT_COSTS["message"].get(model_id, CREDIT_COSTS["message"]["default"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{model_name} ({credit_cost} {get_text('credits_per_message', language, default='kredytów/wiadomość')})", 
                callback_data=f"model_{model_id}"
            )
        ])
    
    # Dodaj przycisk powrotu
    keyboard.append([
        InlineKeyboardButton(get_text("back", language, default="Powrót"), callback_data="menu_section_settings")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )