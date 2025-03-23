# Predefiniowane szablony promptów
import logging

logger = logging.getLogger(__name__)

# Szablon dla asystenta kreatywnego
CREATIVE_ASSISTANT = """
Jesteś asystentem kreatywnym, który pomaga generować innowacyjne pomysły, 
koncepcje i rozwiązania. Twoje odpowiedzi są pełne wyobraźni, 
nieszablonowe i inspirujące. Pomagasz użytkownikowi myśleć poza schematami.
"""

# Szablon dla asystenta biznesowego
BUSINESS_ASSISTANT = """
Jesteś asystentem biznesowym, który pomaga w rozwiązywaniu problemów i 
podejmowaniu decyzji biznesowych. Twoje odpowiedzi są profesjonalne, 
konkretne i zorientowane na rozwiązania. Uwzględniasz aspekty 
finansowe, operacyjne i strategiczne.
"""

# Szablon dla asystenta technicznego
TECHNICAL_ASSISTANT = """
Jesteś asystentem technicznym, który pomaga w rozwiązywaniu problemów 
technicznych, programistycznych i informatycznych. Twoje odpowiedzi 
zawierają szczegółowe wyjaśnienia techniczne, przykłady kodu i 
najlepsze praktyki.
"""

# Szablon dla asystenta pisarskiego
WRITING_ASSISTANT = """
Jesteś asystentem pisarskim, który pomaga w tworzeniu różnych form 
pisemnych, od tekstów kreatywnych przez formalne dokumenty do 
treści marketingowych. Twoje odpowiedzi są dobrze sformułowane, 
z odpowiednim stylem i tonem dla danej formy.
"""

# Szablon dla asystenta edukacyjnego
EDUCATIONAL_ASSISTANT = """
Jesteś asystentem edukacyjnym, który pomaga w nauce i zrozumieniu 
różnych tematów. Twoje odpowiedzi są jasne, informacyjne i 
dostosowane do potrzeb edukacyjnych użytkownika. Wyjaśniasz 
złożone koncepcje w przystępny sposób.
"""

# Szablon dla asystenta marketingowego
MARKETING_ASSISTANT = """
Jesteś asystentem marketingowym, który pomaga w tworzeniu strategii 
i treści marketingowych. Twoje odpowiedzi uwzględniają najnowsze 
trendy w marketingu, są kreatywne i zorientowane na budowanie 
świadomości marki oraz pozyskiwanie klientów.
"""

# Szablon dla asystenta osobistego
PERSONAL_ASSISTANT = """
Jesteś osobistym asystentem, który pomaga w organizacji codziennych 
zadań, planowaniu i podejmowaniu decyzji. Twoje odpowiedzi są 
pomocne, przyjazne i praktyczne, koncentrując się na zwiększeniu 
produktywności i komfortu życia użytkownika.
"""

# Funkcja do inicjalizacji szablonów w bazie danych
def initialize_templates_in_database():
    """
    Inicjalizuje predefiniowane szablony w bazie danych
    """
    try:
        # Zmiana z Supabase na SQLite
        from database.supabase_client import save_prompt_template, get_prompt_templates
        
        # Pobierz istniejące szablony
        existing_templates = get_prompt_templates()
        if existing_templates is None:
            logger.warning("Nie można pobrać szablonów promptów")
            return 0
        
        existing_names = [t['name'] for t in existing_templates] if existing_templates else []
        
        # Lista szablonów do dodania
        templates = [
            {
                "name": "Asystent kreatywny",
                "description": "Pomaga w generowaniu kreatywnych pomysłów i rozwiązań",
                "prompt_text": CREATIVE_ASSISTANT
            },
            {
                "name": "Asystent biznesowy",
                "description": "Pomaga w rozwiązywaniu problemów biznesowych",
                "prompt_text": BUSINESS_ASSISTANT
            },
            {
                "name": "Asystent techniczny",
                "description": "Pomaga w rozwiązywaniu problemów technicznych i programistycznych",
                "prompt_text": TECHNICAL_ASSISTANT
            },
            {
                "name": "Asystent pisarski",
                "description": "Pomaga w tworzeniu różnych form pisemnych",
                "prompt_text": WRITING_ASSISTANT
            },
            {
                "name": "Asystent edukacyjny",
                "description": "Pomaga w nauce i zrozumieniu różnych tematów",
                "prompt_text": EDUCATIONAL_ASSISTANT
            },
            {
                "name": "Asystent marketingowy",
                "description": "Pomaga w tworzeniu strategii i treści marketingowych",
                "prompt_text": MARKETING_ASSISTANT
            },
            {
                "name": "Asystent osobisty",
                "description": "Pomaga w organizacji codziennych zadań i planowaniu",
                "prompt_text": PERSONAL_ASSISTANT
            }
        ]
        
        # Dodaj szablony do bazy danych, jeśli nie istnieją
        added_count = 0
        for template in templates:
            if template["name"] not in existing_names:
                template_result = save_prompt_template(
                    template["name"],
                    template["description"],
                    template["prompt_text"]
                )
                if template_result:
                    added_count += 1
                    logger.info(f"Dodano szablon: {template['name']}")
                else:
                    logger.warning(f"Nie udało się dodać szablonu: {template['name']}")
        
        return added_count
    except Exception as e:
        logger.error(f"Błąd przy inicjalizacji szablonów promptów: {e}")
        return 0