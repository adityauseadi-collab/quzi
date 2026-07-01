"""
Password Strength Validator
============================
Provides both backend validation and strength scoring for passwords.
Used by registration, change-password, and password-reset flows.
"""

import re

# ─── Common weak passwords to block outright ──────────────────────────────────
COMMON_PASSWORDS = {
    'password',
    '12345678', '123456789', '1234567890',
    'qwerty123', 'qwerty1234', 'qwerty',
    'admin123', 'admin1234', 'admin',
    'letmein1', 'welcome1', 'welcome123',
    'iloveyou1', 'sunshine1', 'monkey123',
    'dragon123', 'master123', 'abc12345',
    'passw0rd', 'p@ssword', 'p@ssw0rd',
    'quizmaster', 'quizmaster1',
    'test1234', 'test@123',
    'abc123456', 'football1', 'baseball1',
    'trustno1', 'shadow123', 'michael1',
    'superman1', 'batman123', 'charlie1',
}

# ─── Strength thresholds (score out of 6) ─────────────────────────────────────
WEAK_MAX   = 2   # score 0-2  → Weak
MEDIUM_MAX = 4   # score 3-4  → Medium
# score 5-6 → Strong


def validate_password_strength(password: str) -> dict:
    """
    Validate a password and return strength assessment.

    Returns:
        {
            "valid": True,
            "strength": "Medium",      # "Weak" | "Medium" | "Strong"
            "score": 4,                # 0-6
            "errors": [],
            "suggestions": []
        }
    or:
        {
            "valid": False,
            "strength": "Weak",
            "score": 1,
            "errors": ["Password must be at least 8 characters.", ...],
            "suggestions": ["Add uppercase letters.", ...]
        }
    """
    errors      = []
    suggestions = []
    score       = 0

    if not password:
        return {
            "valid": False,
            "strength": "Weak",
            "score": 0,
            "errors": ["Password is required."],
            "suggestions": [],
        }

    # ── Rule 1: Minimum length ─────────────────────────────────────────────────
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    else:
        score += 1
        if len(password) >= 12:
            score += 1   # bonus for length ≥ 12

    # ── Rule 2: Uppercase letter (REQUIRED) ───────────────────────────────────
    has_upper = bool(re.search(r'[A-Z]', password))
    if not has_upper:
        errors.append("Password must contain at least one uppercase letter (A–Z).")
    else:
        score += 1

    # ── Rule 3: Lowercase letter (REQUIRED) ───────────────────────────────────
    has_lower = bool(re.search(r'[a-z]', password))
    if not has_lower:
        errors.append("Password must contain at least one lowercase letter (a–z).")
    else:
        score += 1

    # ── Rule 4: Number (REQUIRED) ─────────────────────────────────────────────
    has_digit = bool(re.search(r'\d', password))
    if not has_digit:
        errors.append("Password must contain at least one number (0–9).")
    else:
        score += 1

    # ── Rule 5: Special character (OPTIONAL — boosts score) ───────────────────
    has_special = bool(re.search(r'[^A-Za-z0-9]', password))
    if has_special:
        score += 1
    else:
        suggestions.append("Add a special character (e.g. @, #, $, !) to make your password stronger.")

    # ── Rule 6: Common password check ─────────────────────────────────────────
    if password.lower() in COMMON_PASSWORDS:
        errors.append(
            f'"{password}" is a commonly used password and cannot be accepted. '
            "Please choose something unique."
        )
        score = max(0, score - 2)   # heavily penalise

    # ── Determine strength level ───────────────────────────────────────────────
    if score <= WEAK_MAX:
        strength = "Weak"
    elif score <= MEDIUM_MAX:
        strength = "Medium"
    else:
        strength = "Strong"

    # Password is valid only when: no required-rule errors AND at least Medium
    is_valid = (len(errors) == 0) and (strength in ("Medium", "Strong"))

    # Add length suggestion only when valid (encourage going stronger)
    if is_valid and strength == "Medium" and len(password) < 12:
        suggestions.append("Tip: Using 12+ characters makes your password even stronger.")

    return {
        "valid":       is_valid,
        "strength":    strength,
        "score":       score,
        "errors":      errors,
        "suggestions": suggestions,
    }


def get_strength_label(password: str) -> str:
    """Quick helper — returns 'Weak' | 'Medium' | 'Strong'."""
    return validate_password_strength(password)["strength"]


def is_password_strong_enough(password: str) -> bool:
    """Returns True only when password meets the minimum Medium requirement."""
    return validate_password_strength(password)["valid"]
