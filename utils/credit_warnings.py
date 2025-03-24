from utils.translations import get_text
from utils.user_utils import get_user_language
from config import CREDIT_PACKAGES

# utils/credit_warnings.py
"""
Module for credit-related warnings and notifications
"""

def check_operation_cost(user_id, cost, current_credits, operation_name, context):
    """
    Checks if an operation cost is acceptable and returns appropriate warning level
    
    Args:
        user_id (int): User ID
        cost (int): Operation cost in credits
        current_credits (int): User's current credits
        operation_name (str): Name of the operation
        context: Bot context for storing warning levels
        
    Returns:
        dict: Warning information with keys:
            - level: 'none', 'info', 'warning', 'critical'
            - message: Warning message
            - require_confirmation: Whether to require confirmation
    """
    # Pobierz język użytkownika
    language = get_user_language(context, user_id)
    
    # Initialize user data if needed
    if 'user_data' not in context.chat_data:
        context.chat_data['user_data'] = {}
    
    if user_id not in context.chat_data['user_data']:
        context.chat_data['user_data'][user_id] = {}
    
    # Calculate remaining credits after operation
    remaining = current_credits - cost
    
    # Determine warning level
    if cost > current_credits:
        level = 'critical'
        message = get_text("insufficient_credits", language, credits_needed=cost - current_credits)
        require_confirmation = False
    elif cost >= current_credits * 0.7:
        level = 'critical'
        message = get_text("operation_uses_most_credits", language, cost=cost, current=current_credits, percentage=int(cost/current_credits*100))
        require_confirmation = True
    elif cost >= current_credits * 0.5:
        level = 'warning'
        message = get_text("operation_uses_half_credits_detailed", language, cost=cost, current=current_credits)
        require_confirmation = True
    elif cost >= 5:
        level = 'info'
        message = get_text("operation_cost_info", language, cost=cost, remaining=remaining)
        # Check if we've shown info for this operation type recently
        last_warning = context.chat_data['user_data'][user_id].get('last_cost_warning', {})
        if last_warning.get('operation') == operation_name and last_warning.get('count', 0) > 2:
            require_confirmation = False
        else:
            require_confirmation = True
    else:
        level = 'none'
        message = get_text("operation_cost", language, cost=cost)
        require_confirmation = False
    
    # Update last warning information
    if level != 'none':
        if 'last_cost_warning' not in context.chat_data['user_data'][user_id]:
            context.chat_data['user_data'][user_id]['last_cost_warning'] = {}
        
        last_warning = context.chat_data['user_data'][user_id]['last_cost_warning']
        if last_warning.get('operation') == operation_name:
            last_warning['count'] = last_warning.get('count', 0) + 1
        else:
            last_warning['operation'] = operation_name
            last_warning['count'] = 1
    
    return {
        'level': level,
        'message': message,
        'require_confirmation': require_confirmation
    }

def get_low_credits_notification(credits, threshold=10, language="pl"):
    """
    Returns a notification message for low credits if credits are below threshold
    
    Args:
        credits (int): Current credits
        threshold (int): Threshold for low credits warning
        language (str): Language code
        
    Returns:
        str or None: Notification message or None if credits are above threshold
    """
    if credits <= 3:
        return get_text("critically_low_credits", language)
    elif credits <= threshold:
        return get_text("low_credits", language, credits=credits)
    else:
        return None

def format_credit_usage_report(operation, cost, credits_before, credits_after, language="pl"):
    """
    Formats a credit usage report after an operation
    
    Args:
        operation (str): Operation description
        cost (int): Operation cost
        credits_before (int): Credits before operation
        credits_after (int): Credits after operation
        language (str): Language code
        
    Returns:
        str: Formatted credit usage report
    """
    return get_text("credit_usage_report", language, operation=operation, cost=cost, credits_after=credits_after)

def get_credit_recommendation(user_id, context):
    """
    Analyzes user's credit usage pattern and recommends a package
    
    Args:
        user_id (int): User ID
        context: Bot context
        
    Returns:
        dict or None: Recommendation with package_id and reason, or None if no recommendation
    """
    # Get language
    language = get_user_language(context, user_id)
    
    # Get credit usage history from context or database
    from database.credits_client import get_user_credit_stats
    stats = get_user_credit_stats(user_id)
    
    if not stats or not stats.get('usage_history'):
        return None
    
    # Calculate average daily usage over the last week or available period
    history = stats.get('usage_history', [])
    total_usage = sum(transaction['amount'] for transaction in history 
                     if transaction['type'] == 'deduct')
    
    if total_usage == 0:
        return None
    
    # Estimate days of data
    if len(history) >= 7:
        days = 7
    else:
        days = max(1, len(history) // 2)  # Rough estimate
    
    daily_usage = total_usage / days
    
    # Find the best package based on usage
    monthly_usage = daily_usage * 30
    
    recommended_package = None
    for package in CREDIT_PACKAGES:
        if package['credits'] >= monthly_usage:
            if recommended_package is None or package['credits'] < recommended_package['credits']:
                recommended_package = package
    
    if recommended_package:
        days_coverage = recommended_package['credits'] / daily_usage
        return {
            'package_id': recommended_package['id'],
            'package_name': recommended_package['name'],
            'credits': recommended_package['credits'],
            'price': recommended_package['price'],
            'days_coverage': int(days_coverage),
            'reason': get_text("package_recommendation_reason", language, daily_usage=int(daily_usage), days_coverage=int(days_coverage))
        }
    
    return None