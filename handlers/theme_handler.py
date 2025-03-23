# handlers/theme_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.supabase_client import (
    create_conversation_theme, get_user_themes, 
    get_theme_by_id, get_active_themed_conversation
)
from utils.translations import get_text
from handlers.menu_handler import get_user_language

async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tworzy nowy temat konwersacji lub wyświetla listę istniejących tematów
    Użycie: /theme lub /theme [nazwa_tematu]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Jeśli podano nazwę tematu, utwórz nowy temat
    if context.args and len(' '.join(context.args)) > 0:
        theme_name = ' '.join(context.args)
        await create_new_theme(update, context, theme_name)
        return
    
    # W przeciwnym razie wyświetl listę tematów
    await show_themes_list(update, context)

async def create_new_theme(update: Update, context: ContextTypes.DEFAULT_TYPE, theme_name):
    """
    Tworzy nowy temat konwersacji
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Ograniczenie długości nazwy tematu
    if len(theme_name) > 50:
        theme_name = theme_name[:47] + "..."
    
    # Utwórz nowy temat
    theme = create_conversation_theme(user_id, theme_name)
    
    if not theme:
        await update.message.reply_text(
            "Wystąpił błąd podczas tworzenia tematu. Spróbuj ponownie później.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Zapisz aktualny temat w kontekście użytkownika
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    context.chat_data['user_data'][user_id]['current_theme_id'] = theme['id']
    context.chat_data['user_data'][user_id]['current_theme_name'] = theme['theme_name']
    
    # Utwórz konwersację dla tego tematu
    conversation = get_active_themed_conversation(user_id, theme['id'])
    
    # Odpowiedz użytkownikowi
    await update.message.reply_text(
        f"✅ Utworzono nowy temat konwersacji: *{theme_name}*\n\n"
        f"Wszystkie kolejne wiadomości będą przypisane do tego tematu. "
        f"Aby zmienić temat, użyj komendy /theme.\n\n"
        f"Aby wrócić do rozmowy bez tematu, użyj komendy /notheme.",
        parse_mode=ParseMode.MARKDOWN
    )

async def show_themes_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Wyświetla listę tematów konwersacji użytkownika
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Pobierz listę tematów użytkownika
    themes = get_user_themes(user_id)
    
    if not themes:
        await update.message.reply_text(
            "Nie masz jeszcze żadnych tematów konwersacji. "
            "Aby utworzyć nowy temat, użyj komendy /theme [nazwa_tematu].",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Utwórz przyciski dla każdego tematu
    keyboard = []
    for theme in themes:
        keyboard.append([
            InlineKeyboardButton(theme['theme_name'], callback_data=f"theme_{theme['id']}")
        ])
    
    # Dodaj przycisk do utworzenia nowego tematu
    keyboard.append([
        InlineKeyboardButton("➕ Utwórz nowy temat", callback_data="new_theme")
    ])
    
    # Dodaj przycisk do rozmowy bez tematu
    keyboard.append([
        InlineKeyboardButton("🔄 Rozmowa bez tematu", callback_data="no_theme")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Pobierz aktualny temat
    current_theme_id = None
    current_theme_name = "brak"
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        current_theme_id = context.chat_data['user_data'][user_id].get('current_theme_id')
        current_theme_name = context.chat_data['user_data'][user_id].get('current_theme_name', "brak")
    
    await update.message.reply_text(
        f"📑 *Tematy konwersacji*\n\n"
        f"Aktualny temat: *{current_theme_name}*\n\n"
        f"Wybierz temat konwersacji z listy poniżej lub utwórz nowy, "
        f"używając komendy /theme [nazwa_tematu]:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Obsługuje przyciski związane z tematami konwersacji
    """
    query = update.callback_query
    user_id = query.from_user.id
    language = get_user_language(context, user_id)
    
    await query.answer()
    
    # Obsługa przycisku tworzenia nowego tematu
    if query.data == "new_theme":
        await query.edit_message_text(
            "Aby utworzyć nowy temat, użyj komendy /theme [nazwa_tematu]\n\n"
            "Na przykład: /theme Nauka programowania",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Obsługa przycisku rozmowy bez tematu
    if query.data == "no_theme":
        # Usuń aktualny temat z kontekstu użytkownika
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            if 'current_theme_id' in context.chat_data['user_data'][user_id]:
                del context.chat_data['user_data'][user_id]['current_theme_id']
            if 'current_theme_name' in context.chat_data['user_data'][user_id]:
                del context.chat_data['user_data'][user_id]['current_theme_name']
        
        # Utwórz nową konwersację bez tematu
        from database.supabase_client import create_new_conversation
        conversation = create_new_conversation(user_id)
        
        await query.edit_message_text(
            "✅ Przełączono na rozmowę bez tematu.\n\n"
            "Wszystkie kolejne wiadomości będą przypisane do głównej konwersacji.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Obsługa przycisku wyboru tematu
    if query.data.startswith("theme_"):
        theme_id = int(query.data.split("_")[1])
        theme = get_theme_by_id(theme_id)
        
        if not theme:
            await query.edit_message_text(
                "Wystąpił błąd podczas wybierania tematu. Spróbuj ponownie później.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Zapisz aktualny temat w kontekście użytkownika
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['current_theme_id'] = theme['id']
        context.chat_data['user_data'][user_id]['current_theme_name'] = theme['theme_name']
        
        # Pobierz aktywną konwersację dla tego tematu
        conversation = get_active_themed_conversation(user_id, theme['id'])
        
        await query.edit_message_text(
            f"✅ Przełączono na temat: *{theme['theme_name']}*\n\n"
            f"Wszystkie kolejne wiadomości będą przypisane do tego tematu.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

async def notheme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Przełącza na rozmowę bez tematu
    Użycie: /notheme
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Usuń aktualny temat z kontekstu użytkownika
    if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
        if 'current_theme_id' in context.chat_data['user_data'][user_id]:
            del context.chat_data['user_data'][user_id]['current_theme_id']
        if 'current_theme_name' in context.chat_data['user_data'][user_id]:
            del context.chat_data['user_data'][user_id]['current_theme_name']
    
    # Utwórz nową konwersację bez tematu
    from database.supabase_client import create_new_conversation
    conversation = create_new_conversation(user_id)
    
    await update.message.reply_text(
        "✅ Przełączono na rozmowę bez tematu.\n\n"
        "Wszystkie kolejne wiadomości będą przypisane do głównej konwersacji.",
        parse_mode=ParseMode.MARKDOWN
    )