import secrets


def generate_secure_token(length: int=32) -> str:
    """
    Generate a secure random token
    """
    return secrets.token_urlsafe(length)