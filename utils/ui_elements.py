# utils/ui_elements.py
"""Unified module for UI elements and visual styling"""
from utils.translations import get_text

COLOR_SCHEME = {
    'chat': {
        'emoji': '💬',
        'name': 'Chat',
        'primary_color': '#3498db',
        'secondary_color': '#2980b9',
        'border': '🔵'
    },
    'image': {
        'emoji': '🖼️',
        'name': 'Image',
        'primary_color': '#9b59b6',
        'secondary_color': '#8e44ad',
        'border': '🟣'
    },
    'document': {
        'emoji': '📄',
        'name': 'Document',
        'primary_color': '#2ecc71',
        'secondary_color': '#27ae60',
        'border': '🟢'
    },
    'credits': {
        'emoji': '💰',
        'name': 'Credits',
        'primary_color': '#f1c40f',
        'secondary_color': '#f39c12',
        'border': '🟡'
    },
    'settings': {
        'emoji': '⚙️',
        'name': 'Settings',
        'primary_color': '#7f8c8d',
        'secondary_color': '#95a5a6',
        'border': '⚪'
    },
    'help': {
        'emoji': '❓',
        'name': 'Help',
        'primary_color': '#e67e22',
        'secondary_color': '#d35400',
        'border': '🟠'
    },
    'translation': {
        'emoji': '🔤',
        'name': 'Translation',
        'primary_color': '#1abc9c',
        'secondary_color': '#16a085',
        'border': '🟢'
    },
    'analysis': {
        'emoji': '🔍',
        'name': 'Analysis',
        'primary_color': '#34495e',
        'secondary_color': '#2c3e50',
        'border': '⚫'
    },
    'warning': {
        'emoji': '⚠️',
        'name': 'Warning',
        'primary_color': '#e74c3c',
        'secondary_color': '#c0392b',
        'border': '🔴'
    },
    'success': {
        'emoji': '✅',
        'name': 'Success',
        'primary_color': '#2ecc71',
        'secondary_color': '#27ae60',
        'border': '🟢'
    },
    'error': {
        'emoji': '❌',
        'name': 'Error',
        'primary_color': '#e74c3c',
        'secondary_color': '#c0392b',
        'border': '🔴'
    },
    'info': {
        'emoji': 'ℹ️',
        'name': 'Info',
        'primary_color': '#3498db',
        'secondary_color': '#2980b9',
        'border': '🔵'
    },
    'loading': {
        'emoji': '⏳',
        'name': 'Loading',
        'primary_color': '#95a5a6',
        'secondary_color': '#7f8c8d',
        'border': '⚪'
    },
    'tip': {
        'emoji': '💡',
        'name': 'Tip',
        'primary_color': '#f1c40f',
        'secondary_color': '#f39c12',
        'border': '🟡'
    }
}

STATUS_ICONS = {
    'success': '✅',
    'warning': '⚠️',
    'error': '❌',
    'info': 'ℹ️',
    'premium': '⭐',
    'loading': '⏳',
    'low': '🟠',
    'critical': '🔴',
    'good': '🟢'
}

def get_category_style(category):
    return COLOR_SCHEME.get(category.lower(), COLOR_SCHEME['chat'])

def get_category_emoji(category):
    style = get_category_style(category)
    return style['emoji']

def progress_bar(value, max_value, width=10, filled_char='█', empty_char='░'):
    if max_value <= 0:
        return empty_char * width
        
    ratio = min(1.0, value / max_value)
    filled_width = int(width * ratio)
    empty_width = width - filled_width
    
    bar = filled_char * filled_width + empty_char * empty_width
    percentage = int(ratio * 100)
    
    return f"{bar} {percentage}%"

def credit_status_bar(credits, warning_threshold=20, critical_threshold=5, language="pl"):
    if credits <= critical_threshold:
        status = get_text("credit_status_critical", language, default="Extremely low credits!")
        emoji = "🔴"
    elif credits <= warning_threshold:
        status = get_text("credit_status_low", language, default="Low credits")
        emoji = "🟠"
    else:
        status = get_text("credit_status_good", language, default="Good credit balance")
        emoji = "🟢"
    
    max_display = max(100, credits * 2)
    bar = progress_bar(credits, max_display)
    
    return f"{emoji} {get_text('credit_status', language, default='Credit Status')}: {credits}\n{status}\n{bar}"

def color_category_marker(category, text):
    style = get_category_style(category)
    emoji = style['emoji']
    category_name = style['name']
    
    return f"{emoji} *{category_name}*\n\n{text}"

def style_message(message, category='chat'):
    return color_category_marker(category, message)

def create_header(title, category='chat'):
    style = get_category_style(category)
    emoji = style['emoji']
    
    return f"{emoji} *{title}*\n{'─' * (len(title) + 4)}\n"

def section_divider(title=None):
    if title:
        return f"\n\n● *{title}* ●\n{'─' * (len(title) + 4)}\n"
    else:
        return "\n\n" + "─" * 20 + "\n\n"

def create_section(title, content, category='chat'):
    return f"● *{title}* ●\n{content}\n"

def info_card(title, content, category=None):
    emoji = get_category_emoji(category) if category else ""
    
    header = f"┌─── {emoji} *{title}* ───┐"
    footer = "└" + "─" * (len(header) - 2) + "┘"
    
    formatted_content = ""
    for line in content.split('\n'):
        formatted_content += f"│ {line}\n"
    
    return f"{header}\n{formatted_content}{footer}"

def create_status_indicator(status, label=None):
    icon = STATUS_ICONS.get(status.lower(), 'ℹ️')
    
    if label:
        return f"{icon} *{label}*"
    else:
        return icon

def cost_warning(cost, current_credits, operation_name, language="pl"):
    remaining = current_credits - cost
    
    if cost > current_credits:
        status = get_text("insufficient_funds", language, default="Insufficient funds")
        message = get_text("need_more_credits", language, credits_needed=cost - current_credits, 
                         default=f"You need {cost - current_credits} more credits")
    elif cost > current_credits * 0.5:
        status = get_text("high_usage", language, default="High usage")
        message = get_text("operation_uses_half_credits", language, 
                         default="This operation will use more than half of your available credits")
    else:
        status = get_text("cost_info", language, default="Cost information")
        message = get_text("credits_remaining_after_operation", language, remaining=remaining,
                         default=f"You will have {remaining} credits remaining after this operation")
    
    operation_str = get_text("operation", language, default="Operation")
    cost_str = get_text("cost", language, default="Cost")
    current_credits_str = get_text("current_credits", language, default="Current credits")
    credits_str = get_text("credits", language, default="credits")
    
    return f"{status}\n\n{operation_str}: {operation_name}\n*{cost_str}:* {cost} {credits_str}\n*{current_credits_str}:* {current_credits} {credits_str}\n\n{message}"

def feature_badge(feature_name, is_premium=False, cost=None):
    premium_marker = "⭐ " if is_premium else ""
    cost_info = f" ({cost} kr.)" if cost is not None else ""
    
    return f"{premium_marker}{feature_name}{cost_info}"

def animated_loading(step):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    return frames[step % len(frames)]

def usage_tip(tip_text, language="pl"):
    tip_str = get_text("tip", language, default="Tip")
    return f"💡 *{tip_str}:* {tip_text}"