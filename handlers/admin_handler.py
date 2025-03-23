import re
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.supabase_client import create_license

# Lista ID administratorów bota - tutaj należy dodać swoje ID
from config import ADMIN_USER_IDS  # Zastąp swoim ID użytkownika Telegram

async def get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Pobiera informacje o użytkowniku
    Tylko dla administratorów
    Użycie: /userinfo [user_id]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy podano ID użytkownika
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Użycie: /userinfo [user_id]")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID użytkownika musi być liczbą.")
        return
    
    # Pobierz informacje o użytkowniku
    from database.supabase_client import supabase
    
    response = supabase.table('users').select('*').eq('id', target_user_id).execute()
    
    if not response.data:
        await update.message.reply_text("Użytkownik nie istnieje w bazie danych.")
        return
    
    user_data = response.data[0]
    
    # Formatuj dane
    subscription_end = user_data.get('subscription_end_date', 'Brak subskrypcji')
    if subscription_end and subscription_end != 'Brak subskrypcji':
        import datetime
        import pytz
        end_date = datetime.datetime.fromisoformat(subscription_end.replace('Z', '+00:00'))
        subscription_end = end_date.strftime('%d.%m.%Y %H:%M')
    
    info = f"""
*Informacje o użytkowniku:*
ID: `{user_data['id']}`
Nazwa użytkownika: {user_data.get('username', 'Brak')}
Imię: {user_data.get('first_name', 'Brak')}
Nazwisko: {user_data.get('last_name', 'Brak')}
Język: {user_data.get('language_code', 'Brak')}
Subskrypcja do: {subscription_end}
Aktywny: {'Tak' if user_data.get('is_active', False) else 'Nie'}
Data rejestracji: {user_data.get('created_at', 'Brak')}
    """
    
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

async def add_prompt_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dodaje nowy szablon prompta do bazy danych
    Tylko dla administratorów
    Użycie: /addtemplate [nazwa] [opis] [tekst prompta]
    """
    user_id = update.effective_user.id
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy wiadomość jest odpowiedzią na inną wiadomość
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "Ta komenda musi być odpowiedzią na wiadomość zawierającą prompt.\n"
            "Format: /addtemplate [nazwa] [opis]\n"
            "Przykład: /addtemplate \"Asystent kreatywny\" \"Pomaga w kreatywnym myśleniu\""
        )
        return
    
    # Sprawdź, czy podano argumenty
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Użycie: /addtemplate [nazwa] [opis]\n"
            "Przykład: /addtemplate \"Asystent kreatywny\" \"Pomaga w kreatywnym myśleniu\""
        )
        return
    
    # Pobierz tekst prompta z odpowiedzi
    prompt_text = update.message.reply_to_message.text
    
    # Pobierz nazwę i opis
    # Obsługa nazwy i opisu w cudzysłowach
    text = update.message.text[len('/addtemplate '):]
    matches = re.findall(r'"([^"]*)"', text)
    
    if len(matches) < 2:
        await update.message.reply_text(
            "Nieprawidłowy format. Nazwa i opis muszą być w cudzysłowach.\n"
            "Przykład: /addtemplate \"Asystent kreatywny\" \"Pomaga w kreatywnym myśleniu\""
        )
        return
    
    name = matches[0]
    description = matches[1]
    
    # Dodaj szablon do bazy danych
    from database.supabase_client import save_prompt_template
    
    template = save_prompt_template(name, description, prompt_text)
    
    if template:
        await update.message.reply_text(
            f"Dodano nowy szablon prompta:\n"
            f"*Nazwa:* {name}\n"
            f"*Opis:* {description}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Wystąpił błąd podczas dodawania szablonu prompta.")