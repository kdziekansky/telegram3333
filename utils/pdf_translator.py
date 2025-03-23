"""
Moduł do tłumaczenia fragmentów dokumentów PDF
"""
import io
import PyPDF2
import re
import logging
from utils.openai_client import client

logger = logging.getLogger(__name__)

async def extract_first_paragraph(pdf_content):
    """
    Ekstrahuje pierwszy akapit z pliku PDF
    
    Args:
        pdf_content (bytes): Zawartość pliku PDF w formie bajtowej
    
    Returns:
        str: Pierwszy akapit tekstu lub informacja o błędzie
    """
    try:
        # Utwórz obiekt PdfReader z zawartości bajtowej
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Sprawdź, czy PDF ma co najmniej jedną stronę
        if len(pdf_reader.pages) < 1:
            return get_text("pdf_no_pages", language)
        
        # Pobierz tekst z pierwszej strony
        first_page = pdf_reader.pages[0]
        text = first_page.extract_text()
        
        if not text:
            return get_text("pdf_first_page_unreadable", language)
        
        # Podziel tekst na akapity (zakładamy, że akapity są oddzielone podwójnymi znakami nowej linii)
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Znajdź pierwszy niepusty akapit
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph and len(paragraph) > 10:  # Minimalny rozmiar akapitu
                return paragraph
        
        # Jeśli nie znaleziono wyraźnych akapitów, zwróć pierwsze 500 znaków
        if text.strip():
            return text.strip()[:500]
        
        return get_text("pdf_no_paragraphs", language)
    
    except Exception as e:
        logger.error(f"Błąd podczas ekstrahowania akapitu z PDF: {e}")
        return f"Wystąpił błąd podczas odczytywania pliku PDF: {str(e)}"

async def translate_paragraph(text, source_lang="pl", target_lang="en"):
    """
    Tłumaczy tekst z jednego języka na drugi za pomocą OpenAI API
    
    Args:
        text (str): Tekst do przetłumaczenia
        source_lang (str): Język źródłowy (domyślnie "pl")
        target_lang (str): Język docelowy (domyślnie "en")
    
    Returns:
        str: Przetłumaczony tekst lub informacja o błędzie
    """
    try:
        # Przygotuj prompt dla OpenAI API
        messages = [
            {
                "role": "system",
                "content": f"Jesteś profesjonalnym tłumaczem. Przetłumacz podany tekst z języka {source_lang} na język {target_lang}. Zachowaj oryginalny format tekstu."
            },
            {
                "role": "user",
                "content": f"Przetłumacz ten tekst na język {target_lang}:\n\n{text}"
            }
        ]
        
        # Wyślij zapytanie do API
        response = await client.chat.completions.create(
            model="gpt-4o",  # Używamy GPT-4o dla lepszej jakości tłumaczenia
            messages=messages,
            max_tokens=1500  # Zwiększamy limit tokenów dla dłuższych tekstów
        )
        
        # Zwróć tłumaczenie
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Błąd podczas tłumaczenia tekstu: {e}")
        return f"Wystąpił błąd podczas tłumaczenia: {str(e)}"

async def translate_pdf_first_paragraph(pdf_content, source_lang="pl", target_lang="en"):
    """
    Ekstrahuje i tłumaczy pierwszy akapit z pliku PDF
    
    Args:
        pdf_content (bytes): Zawartość pliku PDF w formie bajtowej
        source_lang (str): Język źródłowy (domyślnie "pl")
        target_lang (str): Język docelowy (domyślnie "en")
    
    Returns:
        dict: Słownik zawierający oryginalny tekst i tłumaczenie
    """
    # Ekstrahuj pierwszy akapit
    original_text = await extract_first_paragraph(pdf_content)
    
    # Sprawdź, czy ekstrakcja się powiodła
    if original_text.startswith("Wystąpił błąd") or original_text.startswith("Nie można"):
        return {
            "success": False,
            "original_text": original_text,
            "translated_text": None,
            "error": original_text
        }
    
    # Tłumacz akapit
    translated_text = await translate_paragraph(original_text, source_lang, target_lang)
    
    # Sprawdź, czy tłumaczenie się powiodło
    if translated_text.startswith("Wystąpił błąd"):
        return {
            "success": False,
            "original_text": original_text,
            "translated_text": None,
            "error": translated_text
        }
    
    # Zwróć wyniki
    return {
        "success": True,
        "original_text": original_text,
        "translated_text": translated_text,
        "error": None
    }