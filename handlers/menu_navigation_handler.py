from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.translations import get_text
from utils.user_utils import get_user_language
from utils.menu_manager import update_menu_message, store_menu_state
from config import BOT_NAME

async def handle_back_to_main(update, context):
    """Obsługuje powrót do głównego menu"""
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    # Usuń aktualną wiadomość menu
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Błąd przy usuwaniu wiadomości: {e}")
    
    # Pobierz tekst powitalny i usuń potencjalnie problematyczne znaczniki
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    # Link do zdjęcia bannera
    banner_url = "https://i.imgur.com/YPubLDE.png?v-1123"
    
    # Utwórz klawiaturę menu
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
        # Najpierw próba bez formatowania Markdown
        message = await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=banner_url,
            caption=welcome_text,
            reply_markup=reply_markup
        )
        
        # Zapisz ID wiadomości menu i stan menu
        store_menu_state(context, user_id, 'main', message.message_id)
        
        return True
    except Exception as e:
        print(f"Błąd przy wysyłaniu głównego menu ze zdjęciem: {e}")
        
        # Usuń wszystkie znaki formatowania Markdown
        clean_text = welcome_text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
        
        try:
            message = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=clean_text,
                reply_markup=reply_markup
            )
            
            # Zapisz stan menu
            store_menu_state(context, user_id, 'main', message.message_id)
            
            return True
        except Exception as e2:
            print(f"Błąd przy wysyłaniu fallbacku menu: {e2}")
            
            # Ostatnia próba - podstawowa wiadomość
            try:
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Menu główne",
                    reply_markup=reply_markup
                )
                return True
            except:
                return False
            
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla główne menu bota z przyciskami inline
    """
    user_id = update.effective_user.id
    
    # Upewnij się, że klawiatura systemowa jest usunięta
    await update.message.reply_text("Usuwam klawiaturę...", reply_markup=ReplyKeyboardRemove())
    
    # Pobierz język użytkownika
    language = get_user_language(context, user_id)
    
    # Przygotuj tekst powitalny
    welcome_text = get_text("welcome_message", language, bot_name=BOT_NAME)
    
    # Utwórz klawiaturę menu
    reply_markup = create_main_menu_markup(language)
    
    # Wyślij menu
    message = await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Zapisz ID wiadomości menu i stan menu
    store_menu_state(context, user_id, 'main', message.message_id)
    

def create_main_menu_markup(language):
    """Tworzy klawiaturę dla głównego menu"""
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
        ],
        # Pasek szybkiego dostępu
        [
            InlineKeyboardButton("🆕 " + get_text("new_chat", language, default="Nowa rozmowa"), callback_data="quick_new_chat"),
            InlineKeyboardButton("💬 " + get_text("last_chat", language, default="Ostatnia rozmowa"), callback_data="quick_last_chat"),
            InlineKeyboardButton("💸 " + get_text("buy_credits_btn", language, default="Kup kredyty"), callback_data="quick_buy_credits")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)