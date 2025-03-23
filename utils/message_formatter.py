"""
Moduł do formatowania wiadomości dla bota Telegram
"""
import re
from telegram.constants import ParseMode

def format_markdown_v2(text):
    """
    Formatuje tekst do zgodności z Markdown V2 w Telegramie
    
    Args:
        text (str): Tekst do sformatowania
    
    Returns:
        str: Sformatowany tekst
    """
    # Znaki, które muszą być poprzedzone znakiem ucieczki w Markdown V2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Dodaj znak ucieczki przed każdym specjalnym znakiem
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def truncate_message(message, max_length=4096):
    """
    Skraca wiadomość do maksymalnej długości dozwolonej przez Telegram
    
    Args:
        message (str): Wiadomość do skrócenia
        max_length (int, optional): Maksymalna długość wiadomości. Domyślnie 4096.
    
    Returns:
        str: Skrócona wiadomość
    """
    if len(message) <= max_length:
        return message
    
    # Skróć wiadomość i dodaj informację o skróceniu
    truncated_message = message[:max_length - 50]
    
    # Spróbuj zakończyć na końcu zdania lub paragrafu
    sentence_end = max(
        truncated_message.rfind('.'), 
        truncated_message.rfind('!'), 
        truncated_message.rfind('?'),
        truncated_message.rfind('\n')
    )
    
    if sentence_end > max_length - 150:
        truncated_message = truncated_message[:sentence_end + 1]
    
    return truncated_message + "\n\n[Wiadomość została skrócona ze względu na limity Telegram...]"

def safe_send_message(message):
    """
    Przygotowuje wiadomość do bezpiecznego wysłania przez Telegram
    
    Args:
        message (str): Wiadomość do wysłania
    
    Returns:
        tuple: (sformatowana_wiadomość, tryb_parsowania)
    """
    # Sprawdź, czy wiadomość zawiera znaczniki Markdown
    has_markdown = bool(re.search(r'[*_`\[]', message))
    
    # Jeśli wiadomość zawiera znaczniki Markdown, użyj trybu Markdown
    if has_markdown:
        # Sprawdź, czy wiadomość jest poprawna w Markdown V2
        try:
            # Sprawdź najczęstsze błędy w formatowaniu Markdown
            if '**' in message or '__' in message:
                # Konwertuj na format Markdown używany przez Telegram
                message = message.replace('**', '*').replace('__', '_')
            
            return truncate_message(message), ParseMode.MARKDOWN
        except Exception:
            # W przypadku błędu formatowania, usuń formatowanie
            return truncate_message(message), None
    
    # Jeśli wiadomość nie zawiera formatowania, wyślij jako zwykły tekst
    return truncate_message(message), None

def format_code_block(code, language=""):
    """
    Formatuje blok kodu w formacie Markdown
    
    Args:
        code (str): Kod do sformatowania
        language (str, optional): Język programowania dla podświetlania składni
    
    Returns:
        str: Sformatowany blok kodu
    """
    return f"```{language}\n{code}\n```"

def format_subscription_status(end_date):
    """
    Formatuje datę końca subskrypcji
    
    Args:
        end_date (datetime): Data końca subskrypcji
    
    Returns:
        str: Sformatowana informacja o subskrypcji
    """
    from datetime import datetime
    import pytz
    
    now = datetime.now(pytz.UTC)
    days_left = (end_date - now).days
    
    formatted_date = end_date.strftime('%d.%m.%Y %H:%M')
    
    if days_left > 30:
        return f"Twoja subskrypcja jest aktywna do: *{formatted_date}* (pozostało {days_left} dni)"
    elif days_left > 0:
        return f"Twoja subskrypcja jest aktywna do: *{formatted_date}* (pozostało tylko {days_left} dni!)"
    else:
        return f"Twoja subskrypcja wygasła dnia: {formatted_date}"