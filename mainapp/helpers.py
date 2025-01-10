# helpers.py

import random
import string

def generate_referral_code(user):
    """Generate a referral code based on the user's username."""
    code_length = 8  # Adjust this length if needed
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=code_length))
    return f"{user.username[:4].upper()}-{random_string}"
