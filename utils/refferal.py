"""
Moduł do obsługi programu referencyjnego
"""

# Stałe używane w programie referencyjnym
REFERRAL_CREDITS = 50
REFERRED_BONUS_CREDITS = 25

def generate_referral_code(user_id):
    """Generuje kod referencyjny dla użytkownika"""
    return f"REF{user_id}"

def get_referral_stats(user_id):
    """Pobiera statystyki referencyjne użytkownika"""
    return {
        'code': generate_referral_code(user_id),
        'used_count': 0,
        'earned_credits': 0,
        'referred_users': []
    }

def use_referral_code(user_id, code):
    """Używa kodu referencyjnego"""
    if code.startswith("REF") and code[3:].isdigit():
        referrer_id = int(code[3:])
        if referrer_id == user_id:
            return False, None
        return True, referrer_id
    return False, None