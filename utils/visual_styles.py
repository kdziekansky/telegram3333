# utils/visual_styles.py
"""
Module for visual styles and theming in the bot
"""

# Define color scheme for different message categories
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
    }
}

def get_category_style(category):
    """
    Returns the style information for a category
    
    Args:
        category (str): Category name
        
    Returns:
        dict: Style information or default style if category not found
    """
    return COLOR_SCHEME.get(category.lower(), COLOR_SCHEME['chat'])

def style_message(message, category='chat'):
    """
    Applies visual styling to a message based on category
    
    Args:
        message (str): Original message
        category (str): Message category
        
    Returns:
        str: Styled message
    """
    style = get_category_style(category)
    
    # Add category indicator and border
    styled_message = f"{style['emoji']} *{style['name']}*\n\n{message}"
    
    return styled_message

def create_header(title, category='chat'):
    """
    Creates a styled header for a message
    
    Args:
        title (str): Header title
        category (str): Message category
        
    Returns:
        str: Styled header
    """
    style = get_category_style(category)
    
    header = f"{style['emoji']} *{title}*\n{'─' * (len(title) + 4)}\n"
    return header

def create_section(title, content, category='chat'):
    """
    Creates a styled section with title and content
    
    Args:
        title (str): Section title
        content (str): Section content
        category (str): Message category
        
    Returns:
        str: Styled section
    """
    style = get_category_style(category)
    
    section = f"● *{title}* ●\n{content}\n"
    return section

def create_status_indicator(status, label=None):
    """
    Creates a status indicator based on status value
    
    Args:
        status (str): Status ('success', 'warning', 'error', 'info')
        label (str, optional): Status label
        
    Returns:
        str: Status indicator
    """
    status_map = {
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
    
    icon = status_map.get(status.lower(), 'ℹ️')
    
    if label:
        return f"{icon} *{label}*"
    else:
        return icon