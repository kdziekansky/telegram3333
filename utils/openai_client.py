import openai
from openai import AsyncOpenAI
import base64
import os
import asyncio
from utils.translations import get_text
from config import OPENAI_API_KEY, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT, DALL_E_MODEL
print(f"API Key is {'set' if OPENAI_API_KEY else 'NOT SET'}")
print(f"API Key length: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}")

from httpx import AsyncClient
http_client = AsyncClient()
client = AsyncOpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

import os
os.environ["HTTPX_SKIP_PROXY"] = "true"  # Wyłącza proxy dla httpx

async def chat_completion_stream(messages, model=DEFAULT_MODEL):
    """
    Wygeneruj odpowiedź strumieniową z OpenAI API
    
    Args:
        messages (list): Lista wiadomości w formacie OpenAI
        model (str, optional): Model do użycia. Domyślnie DEFAULT_MODEL.
    
    Returns:
        async generator: Generator zwracający fragmenty odpowiedzi
    """
    try:
        print(f"Wywołuję OpenAI API z modelem {model}")
        # Dodaj opóźnienie w przypadku gdy używamy GPT-4 (aby uniknąć rate limitów)
        if "gpt-4" in model:
            import asyncio
            await asyncio.sleep(0.5)
            
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        error_msg = get_text("openai_stream_error", language, error=str(e))
        print(error_msg)
        yield error_msg


async def chat_completion(messages, model=DEFAULT_MODEL):
    """
    Wygeneruj całą odpowiedź z OpenAI API (niestrumieniowa)
    
    Args:
        messages (list): Lista wiadomości w formacie OpenAI
        model (str, optional): Model do użycia. Domyślnie DEFAULT_MODEL.
    
    Returns:
        str: Wygenerowana odpowiedź
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Błąd API OpenAI: {e}")
        return get_text("openai_response_error", language, error=str(e))

def prepare_messages_from_history(history, user_message, system_prompt=None):
    """
    Przygotuj listę wiadomości dla API OpenAI na podstawie historii konwersacji
    
    Args:
        history (list): Lista wiadomości z historii konwersacji
        user_message (str): Aktualna wiadomość użytkownika
        system_prompt (str, optional): Prompt systemowy. Jeśli None, użyty zostanie DEFAULT_SYSTEM_PROMPT.
    
    Returns:
        list: Lista wiadomości w formacie OpenAI
    """
    # Zabezpieczenie przed None - używamy domyślnego prompta, jeśli system_prompt jest None
    if system_prompt is None:
        system_prompt = DEFAULT_SYSTEM_PROMPT
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Dodaj wiadomości z historii
    for msg in history:
        role = "user" if msg["is_from_user"] else "assistant"
        # Upewniamy się, że content nie jest None
        content = msg["content"] if msg["content"] is not None else ""
        messages.append({
            "role": role,
            "content": content
        })
    
    # Dodaj aktualną wiadomość użytkownika
    messages.append({"role": "user", "content": user_message if user_message is not None else ""})
    
    return messages

async def generate_image_dall_e(prompt):
    """
    Wygeneruj obraz za pomocą DALL-E 3
    
    Args:
        prompt (str): Opis obrazu do wygenerowania
    
    Returns:
        str: URL wygenerowanego obrazu lub błąd
    """
    try:
        response = await client.images.generate(
            model=DALL_E_MODEL,
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        
        return response.data[0].url
    except Exception as e:
        print(f"Błąd generowania obrazu: {e}")
        return None


async def analyze_document(file_content, file_name, mode="analyze", target_language="en"):
    """
    Analizuj lub tłumacz dokument za pomocą OpenAI API
    
    Args:
        file_content (bytes): Zawartość pliku
        file_name (str): Nazwa pliku
        mode (str): Tryb analizy: "analyze" (domyślnie) lub "translate"
        target_language (str): Docelowy język tłumaczenia (dwuliterowy kod)
        
    Returns:
        str: Analiza dokumentu, tłumaczenie lub informacja o błędzie
    """
    try:
        # Określamy typ zawartości na podstawie rozszerzenia pliku
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # Przygotuj odpowiednie instrukcje w zależności od trybu
        if mode == "translate":
            language_names = {
                "en": "English",
                "pl": "Polish",
                "ru": "Russian",
                "fr": "French",
                "de": "German",
                "es": "Spanish",
                "it": "Italian",
                "zh": "Chinese"
            }
            target_lang_name = language_names.get(target_language, target_language)
            
            # Uniwersalne instrukcje niezależne od języka
            system_instruction = f"You are a professional translator. Your task is to translate text from the document to {target_lang_name}. Preserve the original text format."
            user_instruction = f"Translate the text from file {file_name} to {target_lang_name}. Preserve the structure and formatting of the original."
        else:  # tryb analyze
            system_instruction = "You are a helpful assistant who analyzes documents and files."
            user_instruction = f"Analyze file {file_name} and describe its contents. Provide key information and conclusions."
        
        messages = [
            {
                "role": "system", 
                "content": system_instruction
            },
            {
                "role": "user",
                "content": user_instruction
            }
        ]
        
        # Dla plików tekstowych możemy dodać zawartość bezpośrednio
        if file_extension in ['.txt', '.csv', '.md', '.json', '.xml', '.html', '.js', '.py', '.cpp', '.c', '.java']:
            try:
                # Próbuj odkodować jako UTF-8
                file_text = file_content.decode('utf-8')
                messages[1]["content"] += f"\n\nFile content:\n\n{file_text}"
            except UnicodeDecodeError:
                # Jeśli nie możemy odkodować, traktuj jako plik binarny
                messages[1]["content"] += "\n\nThe file contains binary data that cannot be displayed as text."
        
        response = await client.chat.completions.create(
            model="gpt-4o",  # Używamy GPT-4o dla lepszej jakości
            messages=messages,
            max_tokens=1500  # Zwiększamy limit tokenów dla dłuższych tekstów
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Błąd analizy dokumentu: {e}")
        return get_text("document_analysis_error", language, error=str(e))

async def analyze_image(image_content, image_name, mode="analyze", target_language="en"):
    """
    Analizuj obraz za pomocą OpenAI API
    
    Args:
        image_content (bytes): Zawartość obrazu
        image_name (str): Nazwa obrazu
        mode (str): Tryb analizy: "analyze" (domyślnie) lub "translate"
        target_language (str): Docelowy język tłumaczenia (dwuliterowy kod)
        
    Returns:
        str: Analiza obrazu lub tłumaczenie tekstu
    """
    try:
        # Kodowanie obrazu do Base64
        base64_image = base64.b64encode(image_content).decode('utf-8')
        
        # Przygotuj odpowiednie instrukcje bazując na trybie
        if mode == "translate":
            language_names = {
                "en": "English",
                "pl": "Polish",
                "ru": "Russian",
                "fr": "French",
                "de": "German",
                "es": "Spanish",
                "it": "Italian",
                "zh": "Chinese"
            }
            target_lang_name = language_names.get(target_language, target_language)
            
            # Uniwersalne instrukcje niezależne od języka
            system_instruction = f"You are a helpful assistant who translates text from images to {target_lang_name}. Focus only on reading and translating the text visible in the image."
            user_instruction = f"Read all text visible in the image and translate it to {target_lang_name}. Provide only the translation, without additional explanations."
        else:  # tryb analyze
            system_instruction = "You are a helpful assistant who analyzes images. Your answers should be detailed but concise."
            user_instruction = "Describe this image. What do you see? Provide a detailed but concise analysis of the image content."
        
        messages = [
            {
                "role": "system", 
                "content": system_instruction
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_instruction
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o",  # Używamy GPT-4o zamiast zdeprecjonowanego gpt-4-vision-preview
            messages=messages,
            max_tokens=800  # Zwiększona liczba tokenów dla dłuższych tekstów
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Błąd analizy obrazu: {e}")
        return get_text("image_analysis_error", language, error=str(e))