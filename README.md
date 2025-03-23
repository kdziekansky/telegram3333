# Telegram OpenAI Bot

Bot Telegram wykorzystujący modele OpenAI (GPT-4, GPT-4o, GPT-3.5 i DALL-E) do prowadzenia konwersacji, generowania obrazów oraz analizy dokumentów i zdjęć.

## Funkcjonalności

- **Czat z AI** - Rozmowy z różnymi modelami AI (GPT-3.5, GPT-4, GPT-4o)
- **Różne tryby czatu** - Możliwość wyboru spośród wielu predefiniowanych trybów (asystent, programista, kreatywny pisarz itp.)
- **Generowanie obrazów** - Tworzenie obrazów za pomocą DALL-E 3
- **Analiza dokumentów i zdjęć** - Przesyłanie dokumentów i zdjęć do analizy przez AI
- **System kredytów** - System mikropłatności do kontroli wykorzystania zasobów
- **Prywatne konwersacje** - Każdy użytkownik ma swoją prywatną konwersację z botem
- **Eksport rozmów** - Możliwość eksportu historii rozmów do pliku PDF
- **Tematy konwersacji** - Organizacja rozmów w osobne tematy
- **Przypomnienia** - Ustawianie przypomnień o określonych porach
- **Notatki** - Tworzenie i zarządzanie notatkami
- **Analiza kredytów** - Szczegółowa analiza wykorzystania kredytów z wizualizacjami

## Wymagania

- Python 3.9+
- Konto Telegram
- Klucz API OpenAI
- Token bota Telegram
- (Opcjonalnie) Dostęp do API Supabase
- Zainstalowane zależności z pliku requirements.txt

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/twoj-uzytkownik/telegram-openai-bot.git
cd telegram-openai-bot
```

2. Utwórz wirtualne środowisko Python i aktywuj je:
```bash
python -m venv venv
source venv/bin/activate  # Na Windows: venv\Scripts\activate
```

3. Zainstaluj wymagane zależności:
```bash
pip install -r requirements.txt
```

4. Utwórz plik `.env` na podstawie `.env.example` i ustaw swoje klucze API:
```bash
cp .env.example .env
# Edytuj plik .env i uzupełnij wartości
```

## Konfiguracja

### Ustawienia w pliku .env

```
TELEGRAM_TOKEN=twój_token_bota_telegram
OPENAI_API_KEY=twój_klucz_api_openai

# Opcjonalnie dla Supabase
SUPABASE_URL=url_do_twojego_projektu_supabase
SUPABASE_KEY=klucz_api_supabase
```

### Ustawienia bota

Edytuj plik `config.py`, aby dostosować ustawienia bota:
- Zmień nazwę bota i wersję
- Dostosuj predefiniowane tryby czatu
- Ustaw koszty kredytów dla różnych operacji
- Dostosuj pakiety kredytów
- Skonfiguruj limity kontekstu konwersacji

## Uruchomienie

1. Upewnij się, że wirtualne środowisko jest aktywowane:
```bash
source venv/bin/activate  # Na Windows: venv\Scripts\activate
```

2. Uruchom bota:
```bash
python main.py
```

## Baza danych

Bot domyślnie używa SQLite dla przechowywania danych. Baza danych jest inicjalizowana automatycznie przy pierwszym uruchomieniu. Struktura bazy danych jest aktualizowana przy każdym uruchomieniu bota.

### Opcjonalnie: Supabase

Bot obsługuje również Supabase jako alternatywne rozwiązanie bazodanowe. Aby użyć Supabase, ustaw odpowiednie zmienne środowiskowe w pliku `.env`.

## Dostępne komendy

- `/start` - Rozpocznij korzystanie z bota
- `/credits` - Sprawdź stan kredytów
- `/buy` - Kup pakiet kredytów
- `/buy stars` - Kup kredyty za gwiazdki Telegram
- `/status` - Sprawdź status konta
- `/newchat` - Rozpocznij nową konwersację
- `/mode` - Wybierz tryb czatu
- `/models` - Wybierz model AI
- `/image [opis]` - Wygeneruj obraz
- `/export` - Eksportuj konwersację do PDF
- `/theme` - Zarządzaj tematami konwersacji
- `/theme [nazwa]` - Utwórz nowy temat
- `/notheme` - Przełącz na rozmowę bez tematu
- `/remind [czas] [treść]` - Ustaw przypomnienie
- `/reminders` - Pokaż listę przypomnień
- `/note [tytuł] [treść]` - Utwórz notatkę
- `/notes` - Pokaż listę notatek
- `/code [kod]` - Aktywuj kod promocyjny
- `/creditstats` - Analiza wykorzystania kredytów
- `/restart` - Zrestartuj informacje o bocie
- `/menu` - Pokaż menu główne

## Administracja

Bot posiada panel administracyjny dostępny poprzez:
```bash
python web_app.py
```

Panel pozwala na:
- Generowanie kodów aktywacyjnych
- Zarządzanie użytkownikami
- Dodawanie kredytów użytkownikom
- Przeglądanie statystyk

## Modyfikacja

Główne pliki do modyfikacji:
- `config.py` - Konfiguracja
- `handlers/*.py` - Obsługa komend i funkcjonalności
- `utils/*.py` - Narzędzia pomocnicze
- `database/*.py` - Obsługa bazy danych

## Rozwiązywanie problemów

### Komunikacja z API nie działa
- Sprawdź, czy klucze API są poprawnie ustawione w pliku `.env`
- Sprawdź, czy bot ma dostęp do internetu
- Sprawdź limity API dla Twojego konta OpenAI

### Bot nie odpowiada na komendy
- Upewnij się, że bot jest uruchomiony
- Sprawdź, czy nie występują błędy w konsoli
- Użyj komendy `/restart` w bocie
- Użyj skryptu `reset_telegram.py` do zresetowania webhooków

### Problemy z bazą danych
- Uruchom skrypt `update_database.py` aby zaktualizować schemat bazy danych
- Jeśli korzystasz z Supabase, sprawdź połączenie

## Licencja

Ten projekt jest dostępny na licencji MIT.

## Autor

Twój Autor

## Podziękowania

- OpenAI za udostępnienie API
- Twórcom biblioteki python-telegram-bot