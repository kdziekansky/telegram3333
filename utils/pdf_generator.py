# utils/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
import datetime
import re

def generate_conversation_pdf(conversation, user_info, bot_name="AI Bot"):
    """
    Generuje plik PDF z historią konwersacji
    
    Args:
        conversation (list): Lista wiadomości z konwersacji
        user_info (dict): Informacje o użytkowniku
        bot_name (str): Nazwa bota
        
    Returns:
        BytesIO: Bufor zawierający wygenerowany plik PDF
    """
    buffer = io.BytesIO()
    
    # Próba rejestracji fontów z obsługą polskich znaków
    try:
        # Sprawdź, czy fonty DejaVu są dostępne
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
        
        if not os.path.exists(font_dir):
            os.makedirs(font_dir)
        
        # Pobierz DejaVu, jeśli nie istnieje
        dejavu_regular = os.path.join(font_dir, "DejaVuSans.ttf")
        dejavu_bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")
        
        # Jeśli pliki nie istnieją, użyjemy Helvetica
        if os.path.exists(dejavu_regular) and os.path.exists(dejavu_bold):
            pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_regular))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold))
            main_font = 'DejaVuSans'
            bold_font = 'DejaVuSans-Bold'
        else:
            main_font = 'Helvetica'
            bold_font = 'Helvetica-Bold'
    except:
        # Fallback do standardowych fontów
        main_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'
    
    # Konfiguracja dokumentu
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
        title=f"Konwersacja z {bot_name}"
    )
    
    # Style
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='UserMessage',
        parent=styles['Normal'],
        fontName=bold_font,
        spaceAfter=6,
        firstLineIndent=0,
        alignment=0
    ))
    styles.add(ParagraphStyle(
        name='BotMessage',
        parent=styles['Normal'],
        fontName=main_font,
        leftIndent=20,
        spaceAfter=12,
        firstLineIndent=0
    ))
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontName=bold_font,
        alignment=1,
        spaceAfter=12
    ))
    styles.add(ParagraphStyle(
        name='CustomItalic',
        parent=styles['Italic'],
        fontName=main_font,
        spaceAfter=6
    ))
    
    # Funkcja do usuwania znaczników Markdown
    def clean_markdown(text):
        if not text:
            return ""
        # Usuń znaczniki Markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'__(.*?)__', r'\1', text)      # Underline
        text = re.sub(r'_([^_]+)_', r'\1', text)      # Italic
        text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
        text = re.sub(r'`([^`]+)`', r'\1', text)      # Inline code
        text = re.sub(r'```(?:.|\n)*?```', r'[Code block]', text)  # Code block
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)  # Links
        # Escapujemy znaki HTML
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return text
    
    # Elementy dokumentu
    elements = []
    
    # Nagłówek
    title = f"{get_text('conversation_with', language, bot_name=bot_name)}"
    elements.append(Paragraph(title, styles['CustomTitle']))
    
    # Metadane
    current_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    metadata_text = f"{get_text('exported_at', language)}: {current_time}"
    if user_info.get('username'):
        metadata_text += f"<br/>{get_text('user', language)}: {user_info.get('username')}"
    elements.append(Paragraph(metadata_text, styles['CustomItalic']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Treść konwersacji
    for msg in conversation:
        try:
            if msg['is_from_user']:
                icon = "👤 "  # Ikona użytkownika
                style = styles['UserMessage']
                content = f"{icon}{get_text('you', language)}: {clean_markdown(msg['content'])}"
            else:
                icon = "🤖 "  # Ikona bota
                style = styles['BotMessage']
                content = f"{icon}{bot_name}: {clean_markdown(msg['content'])}"
            
            # Dodaj datę i godzinę wiadomości, jeśli są dostępne
            if 'created_at' in msg and msg['created_at']:
                try:
                    # Konwersja formatu daty
                    if isinstance(msg['created_at'], str) and 'T' in msg['created_at']:
                        dt = datetime.datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
                        time_str = dt.strftime("%d-%m-%Y %H:%M")
                        content += f"<br/><font size=8 color=gray>{time_str}</font>"
                except:
                    pass
            
            elements.append(Paragraph(content, style))
        except Exception as e:
            # W przypadku błędu dodaj informację
            elements.append(Paragraph(f"Błąd formatowania wiadomości: {str(e)}", styles['Normal']))
    
    # Stopka
    elements.append(Spacer(1, 1*cm))
    footer_text = f"{get_text('generated_by', language)} {bot_name} • {current_time}"
    elements.append(Paragraph(footer_text, styles['CustomItalic']))
    
    # Wygeneruj dokument
    doc.build(elements)
    
    # Zresetuj pozycję w buforze i zwróć go
    buffer.seek(0)
    return buffer