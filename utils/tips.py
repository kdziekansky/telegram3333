# utils/tips.py
"""
Module for managing usage tips and contextual help
"""
import random
from utils.translations import get_text
from utils.user_utils import get_user_language

def get_general_tips(language="pl"):
    """Get list of general tips in specific language"""
    return [
        get_text("tip_shorter_questions", language),
        get_text("tip_model_selection", language),
        get_text("tip_save_credits_with_mode", language),
        get_text("tip_previous_conversation", language),
        get_text("tip_specific_questions", language)
    ]

def get_credits_tips(language="pl"):
    """Get list of credit-related tips in specific language"""
    return [
        get_text("tip_referral_program", language),
        get_text("tip_bulk_purchase", language),
        get_text("tip_low_credits_notification", language),
        get_text("tip_gpt35_cheaper", language),
        get_text("tip_monthly_subscription", language)
    ]

def get_image_tips(language="pl"):
    """Get list of image-related tips in specific language"""
    return [
        get_text("tip_image_quality", language),
        get_text("tip_image_details", language),
        get_text("tip_image_style", language),
        get_text("tip_image_lighting", language),
        get_text("tip_image_variants", language)
    ]

def get_document_tips(language="pl"):
    """Get list of document-related tips in specific language"""
    return [
        get_text("tip_document_text_clarity", language),
        get_text("tip_document_multipage", language),
        get_text("tip_document_pdf", language),
        get_text("tip_document_quality", language),
        get_text("tip_document_specific_pages", language)
    ]

def get_onboarding_tips(language="pl"):
    """Get list of onboarding tips in specific language"""
    return [
        get_text("tip_onboarding_welcome", language),
        get_text("tip_onboarding_modes", language),
        get_text("tip_onboarding_documents", language),
        get_text("tip_onboarding_images", language),
        get_text("tip_onboarding_credits", language)
    ]

def get_random_tip(category=None, language="pl"):
    """
    Returns a random tip, optionally from a specific category
    
    Args:
        category (str, optional): Category of tips ('general', 'credits', 'image', 'document', 'onboarding')
        language (str): Language code for the tip
        
    Returns:
        str: Random tip
    """
    if category == 'general':
        tips = get_general_tips(language)
    elif category == 'credits':
        tips = get_credits_tips(language)
    elif category == 'image':
        tips = get_image_tips(language)
    elif category == 'document':
        tips = get_document_tips(language)
    elif category == 'onboarding':
        tips = get_onboarding_tips(language)
    else:
        # Combine all tips except onboarding
        tips = (get_general_tips(language) + get_credits_tips(language) + 
                get_image_tips(language) + get_document_tips(language))
    
    return random.choice(tips)

def should_show_tip(user_id, context, frequency=5):
    """
    Determines if a tip should be shown based on user's interaction count
    
    Args:
        user_id (int): User's ID
        context: Bot context
        frequency (int): How often to show tips (every X interactions)
        
    Returns:
        bool: Whether to show a tip
    """
    # Initialize if needed
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    if 'interaction_count' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['interaction_count'] = 0
        context.chat_data['user_data'][user_id]['tips_enabled'] = True
    
    # Increment interaction count
    context.chat_data['user_data'][user_id]['interaction_count'] += 1
    
    # Check if tips are enabled and if it's time to show one
    return (context.chat_data['user_data'][user_id]['tips_enabled'] and 
            context.chat_data['user_data'][user_id]['interaction_count'] % frequency == 0)

def toggle_tips(user_id, context, enabled=None):
    """
    Toggles or sets the tips display setting for a user
    
    Args:
        user_id (int): User's ID
        context: Bot context
        enabled (bool, optional): If provided, sets to this value; otherwise toggles
        
    Returns:
        bool: New setting value
    """
    # Initialize if needed
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    if 'tips_enabled' not in context.chat_data['user_data'][user_id]:
        context.chat_data['user_data'][user_id]['tips_enabled'] = True
    
    # Set or toggle
    if enabled is not None:
        context.chat_data['user_data'][user_id]['tips_enabled'] = enabled
    else:
        context.chat_data['user_data'][user_id]['tips_enabled'] = not context.chat_data['user_data'][user_id]['tips_enabled']
    
    return context.chat_data['user_data'][user_id]['tips_enabled']

def get_contextual_tip(category, context, user_id):
    """
    Gets a contextual tip based on user's current activity
    
    Args:
        category (str): Category of current activity
        context: Bot context
        user_id (int): User's ID
        
    Returns:
        str: Tip text or None if no tip should be shown
    """
    # Check if we should show a tip
    if not should_show_tip(user_id, context):
        return None
    
    # Get the user's language
    language = get_user_language(context, user_id)
    
    # Get a tip from the relevant category
    if category in ['chat', 'message']:
        return get_random_tip('general', language)
    elif category in ['credits', 'buy']:
        return get_random_tip('credits', language)
    elif category == 'image':
        return get_random_tip('image', language)
    elif category in ['document', 'pdf', 'translation']:
        return get_random_tip('document', language)
    else:
        return get_random_tip(language=language)