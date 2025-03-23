import requests
import os
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych
load_dotenv()

def reset_telegram_bot():
    """
    Resetuje webhooki i usuwa oczekujące aktualizacje dla bota Telegram.
    Useful when getting "Conflict: terminated by other getUpdates request" errors.
    """
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("Błąd: Brak tokena Telegram w zmiennych środowiskowych.")
        return False
    
    # URL do usunięcia webhooka i oczekujących aktualizacji
    url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('ok'):
            print("Webhook został usunięty, a oczekujące aktualizacje zresetowane!")
            print(f"Odpowiedź: {data}")
            return True
        else:
            print(f"Błąd: {data.get('description', 'Nieznany błąd')}")
            return False
    except Exception as e:
        print(f"Wyjątek podczas resetowania webhooka: {e}")
        return False

if __name__ == "__main__":
    reset_telegram_bot()