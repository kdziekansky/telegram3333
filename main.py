import os
# Wyłącz wszystkie ustawienia proxy
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ["HTTPX_SKIP_PROXY"] = "true"

import logging
logging.basicConfig(level=logging.INFO)
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TELEGRAM_TOKEN
from telegram import Update
from telegram.ext import ContextTypes

# Napraw problem z proxy w httpx
from telegram.request import HTTPXRequest

# Nadpisz metodę _build_client
original_build_client = HTTPXRequest._build_client

def patched_build_client(self):
    if hasattr(self, '_client_kwargs') and 'proxies' in self._client_kwargs:
        del self._client_kwargs['proxies']
    return original_build_client(self)

# Podmieniamy metodę
HTTPXRequest._build_client = patched_build_client

# Import handlerów komend
from handlers.start_handler import start_command, language_command
from handlers.help_handler import help_command
from handlers.basic_commands import restart_command, check_status, new_chat
from handlers.mode_handler import show_modes
from handlers.export_handler import export_conversation
from handlers.credit_handler import credits_command, buy_command, credit_stats_command
from handlers.code_handler import code_command, admin_generate_code
from handlers.image_handler import generate_image
from handlers.translate_handler import translate_command
from handlers.payment_handler import payment_command, subscription_command, transactions_command
from handlers.admin_handler import get_user_info
from handlers.admin_package_handler import add_package, list_packages, toggle_package, add_default_packages
from handlers.onboarding_handler import onboarding_command

# Import handlerów wiadomości
from handlers.message_handler import message_handler
from handlers.file_handler import handle_document, handle_photo

# Import centralnego routera callbacków
from handlers.callback_router import route_callback

# Inicjalizacja aplikacji
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Rejestracja handlerów komend
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("status", check_status))
application.add_handler(CommandHandler("newchat", new_chat))
application.add_handler(CommandHandler("restart", restart_command))
application.add_handler(CommandHandler("mode", show_modes))
application.add_handler(CommandHandler("image", generate_image))
application.add_handler(CommandHandler("export", export_conversation))
application.add_handler(CommandHandler("language", language_command))
application.add_handler(CommandHandler("onboarding", onboarding_command))
application.add_handler(CommandHandler("translate", translate_command))
application.add_handler(CommandHandler("credits", credits_command))
application.add_handler(CommandHandler("buy", buy_command))
application.add_handler(CommandHandler("creditstats", credit_stats_command))
application.add_handler(CommandHandler("payment", payment_command))
application.add_handler(CommandHandler("subscription", subscription_command))
application.add_handler(CommandHandler("transactions", transactions_command))
application.add_handler(CommandHandler("code", code_command))

# Handlery dla administratorów
application.add_handler(CommandHandler("addpackage", add_package))
application.add_handler(CommandHandler("listpackages", list_packages))
application.add_handler(CommandHandler("togglepackage", toggle_package))
application.add_handler(CommandHandler("adddefaultpackages", add_default_packages))
application.add_handler(CommandHandler("gencode", admin_generate_code))
application.add_handler(CommandHandler("userinfo", get_user_info))

# Centralny handler wszystkich callbacków
application.add_handler(CallbackQueryHandler(route_callback))

# Handler wiadomości tekstowych
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Handler dokumentów i zdjęć
application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Uruchomienie bota
if __name__ == "__main__":
    print("Bot uruchomiony. Naciśnij Ctrl+C, aby zatrzymać.")
    application.run_polling()