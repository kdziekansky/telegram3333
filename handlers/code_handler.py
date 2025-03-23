"""
Moduł do obsługi kodów aktywacyjnych
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from utils.translations import get_text
from database.credits_client import get_user_credits
from utils.user_utils import get_user_language

# Prosta tymczasowa implementacja funkcji activate_code
def activate_code(user_id, code):
    """
    Aktywuje kod dla użytkownika (tymczasowa implementacja)
    
    Args:
        user_id (int): ID użytkownika
        code (str): Kod aktywacyjny
        
    Returns:
        tuple: (Czy aktywacja się powiodła, liczba kredytów)
    """
    # Obsługa przykładowych kodów dla demonstracji
    if code == "DEMO100":
        from database.credits_client import add_user_credits
        add_user_credits(user_id, 100, f"Aktywacja kodu {code}")
        return True, 100
    elif code == "DEMO500":
        from database.credits_client import add_user_credits
        add_user_credits(user_id, 500, f"Aktywacja kodu {code}")
        return True, 500
        
    return False, 0

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Aktywuje kod promocyjny
    Użycie: /code [kod]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy podano kod
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            get_text("activation_code_usage", language),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    code = context.args[0].upper()  # Konwertuj na wielkie litery dla spójności
    
    # Aktywuj kod
    success, credits = activate_code(user_id, code)
    
    if success:
        # Pobierz aktualny stan kredytów
        total_credits = get_user_credits(user_id)
        
        await update.message.reply_text(
            get_text("activation_code_success", language, 
                    code=code,
                    credits=credits,
                    total=total_credits),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            get_text("activation_code_invalid", language),
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_generate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generuje nowy kod aktywacyjny (tylko dla administratorów)
    Użycie: /gencode [liczba_kredytów] [liczba_kodów]
    """
    user_id = update.effective_user.id
    
    # Lista ID administratorów bota
    from config import ADMIN_USER_IDS  # Należy zaktualizować do rzeczywistych ID administracyjnych
    
    # Sprawdź, czy użytkownik jest administratorem
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Nie masz uprawnień do tej komendy.")
        return
    
    # Sprawdź, czy podano wystarczającą liczbę argumentów
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Użycie: /gencode [liczba_kredytów] [liczba_kodów]\n"
            "Na przykład: /gencode 100 5 - wygeneruje 5 kodów po 100 kredytów każdy"
        )
        return
    
    try:
        credits = int(context.args[0])
        count = int(context.args[1]) if len(context.args) > 1 else 1
    except ValueError:
        await update.message.reply_text("Nieprawidłowe argumenty. Użyj liczb, np. /gencode 100 5")
        return
    
    # Ogranicz liczbę kodów do 20 na raz, aby uniknąć spamu
    if count > 20:
        count = 20
    
    # Generuj demonstracyjne kody (w rzeczywistej implementacji użylibyśmy funkcji z utils/activation_codes.py)
    import random
    import string
    
    def generate_code():
        prefix = "DEMO"
        suffix = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        return f"{prefix}{suffix}"
    
    codes = [generate_code() for _ in range(count)]
    
    if codes:
        codes_text = "\n".join(codes)
        message = f"Wygenerowane kody ({count} x {credits} kredytów):\n\n{codes_text}"
        
        # Jeśli wiadomość jest zbyt długa, wyślij plik
        if len(message) > 4000:
            from io import BytesIO
            file = BytesIO(codes_text.encode('utf-8'))
            file.name = f"kody_{credits}_kredytow.txt"
            await update.message.reply_document(file)
        else:
            await update.message.reply_text(message)
    else:
        await update.message.reply_text("Wystąpił błąd podczas generowania kodów.")