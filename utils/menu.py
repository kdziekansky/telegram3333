# utils/menu.py
"""
Unified module for menu management and UI handling
"""
import logging
from telegram import InlineKeyboardMarkup
from telegram.constants import ParseMode
from utils.translations import get_text
from utils.user_utils import get_user_language

logger = logging.getLogger(__name__)

class MenuState:
    """Class for managing menu state"""
    
    def __init__(self):
        self.states = {}  # user_id -> menu state
        self.message_ids = {}  # user_id -> menu message ID
    
    def set_state(self, user_id, state):
        """Sets the menu state for a user"""
        self.states[user_id] = state
    
    def get_state(self, user_id, default='main'):
        """Gets the menu state for a user"""
        return self.states.get(user_id, default)
    
    def set_message_id(self, user_id, message_id):
        """Saves the menu message ID for a user"""
        self.message_ids[user_id] = message_id
    
    def get_message_id(self, user_id):
        """Gets the menu message ID for a user"""
        return self.message_ids.get(user_id)
    
    def save_to_context(self, context, user_id):
        """Saves the menu state to context"""
        if 'user_data' not in context.chat_data:
            context.chat_data['user_data'] = {}
        
        if user_id not in context.chat_data['user_data']:
            context.chat_data['user_data'][user_id] = {}
        
        context.chat_data['user_data'][user_id]['menu_state'] = self.get_state(user_id)
        if self.get_message_id(user_id):
            context.chat_data['user_data'][user_id]['menu_message_id'] = self.get_message_id(user_id)
    
    def load_from_context(self, context, user_id):
        """Loads the menu state from context"""
        if 'user_data' in context.chat_data and user_id in context.chat_data['user_data']:
            user_data = context.chat_data['user_data'][user_id]
            if 'menu_state' in user_data:
                self.set_state(user_id, user_data['menu_state'])
            if 'menu_message_id' in user_data:
                self.set_message_id(user_id, user_data['menu_message_id'])

# Create a global instance for tracking menu state
menu_state = MenuState()

def store_menu_state(context, user_id, state, message_id=None):
    """
    Stores the menu state for a user
    
    Args:
        context: Bot context
        user_id: User ID
        state: Menu state (e.g. 'main', 'chat_modes', 'credits', etc.)
        message_id: ID of the menu message (optional)
    """
    menu_state.set_state(user_id, state)
    if message_id:
        menu_state.set_message_id(user_id, message_id)
    menu_state.save_to_context(context, user_id)
    logger.debug(f"Saved menu state '{state}' for user {user_id}")

def get_menu_state(context, user_id):
    """
    Retrieves the menu state for a user
    
    Args:
        context: Bot context
        user_id: User ID
        
    Returns:
        str: Menu state
    """
    menu_state.load_from_context(context, user_id)
    return menu_state.get_state(user_id)

def get_menu_message_id(context, user_id):
    """
    Retrieves the ID of the menu message for a user
    
    Args:
        context: Bot context
        user_id: User ID
        
    Returns:
        int: Menu message ID
    """
    menu_state.load_from_context(context, user_id)
    return menu_state.get_message_id(user_id)

async def update_menu(query, text, keyboard, parse_mode=None):
    """
    Updates a menu message
    
    Args:
        query: callback_query object
        text: Text to display
        keyboard: Keyboard with buttons
        parse_mode: Formatting mode (optional)
        
    Returns:
        bool: Whether the update was successful
    """
    try:
        # Check if the message has a caption (photo) or is plain text
        is_caption = hasattr(query.message, 'caption') and query.message.caption is not None
        
        # Try to update with formatting
        if is_caption:
            if parse_mode:
                await query.edit_message_caption(
                    caption=text, reply_markup=keyboard, parse_mode=parse_mode
                )
            else:
                await query.edit_message_caption(
                    caption=text, reply_markup=keyboard
                )
        else:
            if parse_mode:
                await query.edit_message_text(
                    text=text, reply_markup=keyboard, parse_mode=parse_mode
                )
            else:
                await query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
        return True
    
    except Exception as e:
        logger.error(f"Menu update error: {e}")
        
        # If there was a formatting error, try without formatting
        if parse_mode:
            try:
                # Remove formatting markers
                text = text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
                
                if is_caption:
                    await query.edit_message_caption(
                        caption=text, reply_markup=keyboard
                    )
                else:
                    await query.edit_message_text(
                        text=text, reply_markup=keyboard
                    )
                return True
            except Exception as e2:
                logger.error(f"Second menu update error: {e2}")
        
        # Last resort - send a new message
        try:
            # Save chat_id because we'll be deleting the message
            chat_id = query.message.chat_id
            
            # Send a new message
            await query.bot.send_message(
                chat_id=chat_id,
                text=text.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", ""),
                reply_markup=keyboard
            )
            return True
        except Exception as e3:
            logger.error(f"Cannot send new message: {e3}")
            return False

def create_menu_buttons(button_configs, language):
    """
    Creates menu buttons based on configuration
    
    Args:
        button_configs (list): List of button configurations
        language (str): Language code
    
    Returns:
        InlineKeyboardMarkup: Keyboard with buttons
    """
    keyboard = []
    
    for row_config in button_configs:
        row = []
        for button_config in row_config:
            if isinstance(button_config, tuple) and len(button_config) == 2:
                text_key, callback_data = button_config
                button_text = get_text(text_key, language)
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            elif isinstance(button_config, tuple) and len(button_config) == 3:
                text_key, callback_data, prefix = button_config
                button_text = f"{prefix} {get_text(text_key, language)}"
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
            elif isinstance(button_config, dict):
                # For buttons with URL
                text_key = button_config.get('text_key')
                url = button_config.get('url')
                button_text = get_text(text_key, language)
                row.append(InlineKeyboardButton(button_text, url=url))
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def safe_markdown(text):
    """
    Prepares text for safe Markdown formatting
    
    Args:
        text (str): Text to secure
    
    Returns:
        str: Secured text
    """
    if not text:
        return ""
    
    # Make sure we have a string
    text = str(text)
    
    # Fix the most problematic elements
    
    # 1. Make sure asterisks are paired
    if text.count('*') % 2 != 0:
        text = text.replace('*', '\\*')
    
    # 2. Make sure underscores are paired
    if text.count('_') % 2 != 0:
        text = text.replace('_', '\\_')
    
    # 3. Make sure backticks are paired
    if text.count('`') % 2 != 0:
        text = text.replace('`', '\\`')
    
    # 4. Avoid problematic sequences
    text = text.replace('__', '\\_\\_')
    text = text.replace('**', '\\*\\*')
    
    return text

def get_navigation_path(state, language):
    """
    Generates a navigation bar text
    
    Args:
        state: Menu state (e.g. 'main', 'chat_modes', 'credits', etc.)
        language: Language code
        
    Returns:
        str: Navigation bar text
    """
    # Mapping menu states to navigation paths
    navigation_map = {
        'main': get_text("main_menu", language, default="Menu główne"),
        'chat_modes': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_chat_mode', language, default='Tryb czatu')}",
        'credits': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_credits', language, default='Kredyty')}",
        'settings': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_settings', language, default='Ustawienia')}",
        'history': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_dialog_history', language, default='Historia')}",
        'help': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('menu_help', language, default='Pomoc')}",
        'image': f"{get_text('main_menu', language, default='Menu główne')} > {get_text('image_generate', language, default='Generowanie obrazu')}"
    }
    
    return navigation_map.get(state, get_text("main_menu", language, default="Menu główne"))