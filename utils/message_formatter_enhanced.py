# utils/message_formatter_enhanced.py
"""
Enhanced module for formatting messages with improved visual elements
This extends the functionality of the original message_formatter.py
"""
from utils.message_formatter import truncate_message, format_markdown_v2, safe_send_message
from telegram.constants import ParseMode

def format_long_message(message, max_section_length=500):
    """
    Formats a long message with section dividers for better readability
    
    Args:
        message (str): Original message
        max_section_length (int): Maximum length of each section
        
    Returns:
        str: Formatted message with dividers
    """
    # If message is short, return as is
    if len(message) <= max_section_length:
        return message
    
    # Split into paragraphs
    paragraphs = message.split('\n\n')
    
    # Group paragraphs into sections
    sections = []
    current_section = []
    current_length = 0
    
    for paragraph in paragraphs:
        if current_length + len(paragraph) > max_section_length and current_section:
            sections.append('\n\n'.join(current_section))
            current_section = [paragraph]
            current_length = len(paragraph)
        else:
            current_section.append(paragraph)
            current_length += len(paragraph)
    
    # Add the last section
    if current_section:
        sections.append('\n\n'.join(current_section))
    
    # Join sections with dividers
    formatted_message = ""
    for i, section in enumerate(sections):
        if i > 0:
            formatted_message += "\n\n" + "─" * 20 + "\n\n"
        formatted_message += section
    
    return formatted_message

def format_credit_info(credits, cost=None, operation=None):
    """
    Formats credit information as a card
    
    Args:
        credits (int): Current credits
        cost (int, optional): Cost of operation
        operation (str, optional): Operation description
        
    Returns:
        str: Formatted credit information
    """
    from utils.ui_elements import credit_status_bar
    
    status_bar = credit_status_bar(credits)
    
    if cost and operation:
        remaining = credits - cost
        operation_info = f"*Operacja:* {operation}\n*Koszt:* {cost} kredytów\n*Pozostanie:* {remaining} kredytów"
        return f"{status_bar}\n\n{operation_info}"
    else:
        return status_bar

def format_transaction_report(cost, credits_before, credits_after, operation):
    """
    Formats a transaction report after an operation
    
    Args:
        cost (int): Operation cost
        credits_before (int): Credits before operation
        credits_after (int): Credits after operation
        operation (str): Operation description
        
    Returns:
        str: Formatted transaction report
    """
    return get_text("transaction_report", language, operation=operation, cost=cost, credits_before=credits_before, credits_after=credits_after)

def format_onboarding_step(step_number, total_steps, title, description, action_text):
    """
    Formats an onboarding step message
    
    Args:
        step_number (int): Current step number
        total_steps (int): Total number of steps
        title (str): Step title
        description (str): Step description
        action_text (str): Text explaining what action to take
        
    Returns:
        str: Formatted onboarding step
    """
    from utils.ui_elements import progress_bar
    
    progress = get_text("step_progress", language, current=step_number, total=total_steps)
    bar = progress_bar(step_number, total_steps)
    
    return f"*{progress}*\n{bar}\n\n*{title}*\n\n{description}\n\n*Co zrobić:*\n{action_text}"

def stylize_response(response, category="chat"):
    """
    Adds style elements to bot responses based on category
    
    Args:
        response (str): Original response text
        category (str): Response category (chat, image, document, credits, etc.)
        
    Returns:
        str: Styled response
    """
    from utils.ui_elements import color_category_marker
    
    # Truncate if needed
    response = truncate_message(response)
    
    # Add category styling
    styled_response = color_category_marker(category, response)
    
    return styled_response

def enhance_credits_display(credits, bot_name):
    """
    Creates an enhanced credit status display
    
    Args:
        credits (int): Current credits
        bot_name (str): Name of the bot
        
    Returns:
        str: Enhanced credit status display
    """
    from utils.ui_elements import credit_status_bar, info_card
    
    status_bar = credit_status_bar(credits)
    
    content = (
        f"*{get_text('available_credits', language)}:* {credits}\n\n"
        f"{status_bar}\n\n"
        f"{get_text('use_credits_wisely', language)}"
    )
    
    return info_card(f"{bot_name} - {get_text('credit_status', language)}", content, category="credits")

def format_mode_selection(mode_name, mode_description, credit_cost, model_name):
    """
    Formats a mode selection confirmation message
    
    Args:
        mode_name (str): Name of the selected mode
        mode_description (str): Description of the mode
        credit_cost (int): Cost in credits
        model_name (str): Name of the model used
        
    Returns:
        str: Formatted mode selection message
    """
    from utils.ui_elements import info_card
    
    premium_indicator = "⭐ " if credit_cost > 1 else ""
    
    content = (
        f"*{get_text('description', language)}:* {mode_description}\n\n"
        f"*{get_text('current_model', language)}:* {model_name}\n"
        f"*{get_text('cost', language)}:* {credit_cost} {get_text('credits_per_message', language)}\n\n"
        f"{get_text('ask_question_now', language)}"
    )
    
    return info_card(f"{premium_indicator}{get_text('selected_mode', language)}: {mode_name}", content, category="chat")

def enhance_help_message(help_text):
    """
    Enhances the default help message with better formatting
    
    Args:
        help_text (str): Original help text
        
    Returns:
        str: Enhanced help message
    """
    from utils.ui_elements import section_divider
    
    # Split the text into sections based on common pattern
    sections = []
    current_section = ""
    lines = help_text.split('\n')
    
    for line in lines:
        if line.startswith('**') or line.startswith('#') or line.startswith('-'):
            # This looks like a section header
            if current_section:
                sections.append(current_section)
                current_section = ""
        
        current_section += line + '\n'
    
    # Add the last section
    if current_section:
        sections.append(current_section)
    
    # Join sections with dividers
    enhanced_text = ""
    for i, section in enumerate(sections):
        if i > 0:
            # Try to extract section title
            lines = section.split('\n')
            if lines and (lines[0].startswith('**') or lines[0].startswith('#')):
                title = lines[0].replace('**', '').replace('#', '').strip()
                enhanced_text += section_divider(title)
                # Remove the title from the section as it's now in the divider
                section = '\n'.join(lines[1:])
            else:
                enhanced_text += section_divider()
        
        enhanced_text += section
    
    return enhanced_text