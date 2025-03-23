from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
# Usuń importy stałych i użyj get_text
# from config import LICENSE_ACTIVATED_MESSAGE, INVALID_LICENSE_MESSAGE, SUBSCRIPTION_EXPIRED_MESSAGE
from utils.translations import get_text
from utils.user_utils import get_user_language
from database.supabase_client import activate_user_license, check_active_subscription, get_subscription_end_date

async def activate_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Aktywuje licencję dla użytkownika
    Użycie: /activate [klucz_licencyjny]
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy podano klucz licencyjny
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Użycie: /activate [klucz_licencyjny]")
        return
    
    license_key = context.args[0]
    
    # Aktywuj licencję
    success, end_date = activate_user_license(user_id, license_key)
    
    if success and end_date:
        formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
        # Użyj get_text zamiast stałej
        message = get_text("license_activated", language, end_date=formatted_date, 
                          default="✅ Licencja została aktywowana pomyślnie!\nData wygaśnięcia: *{end_date}*")
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        # Użyj get_text zamiast stałej
        await update.message.reply_text(get_text("invalid_license", language, 
                                        default="❌ Nieprawidłowy klucz licencyjny. Sprawdź klucz i spróbuj ponownie."))

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sprawdza status subskrypcji użytkownika
    Użycie: /status
    """
    user_id = update.effective_user.id
    language = get_user_language(context, user_id)
    
    # Sprawdź, czy użytkownik ma aktywną subskrypcję
    if check_active_subscription(user_id):
        end_date = get_subscription_end_date(user_id)
        formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
        
        message = f"Twoja subskrypcja jest aktywna.\nData wygaśnięcia: *{formatted_date}*"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        # Użyj get_text zamiast stałej
        await update.message.reply_text(get_text("subscription_expired", language, 
                                        default="⚠️ Twoja subskrypcja wygasła. Aby kontynuować korzystanie z bota, kup nowy pakiet lub aktywuj kod promocyjny."))