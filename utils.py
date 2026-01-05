import hashlib, hmac, secrets, string
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

def generate_code(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def hash_code(code:str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def codes_match(hash_a: str, code_plain: str) -> bool:
    return hmac.compare_digest(hash_a, hash_code(code_plain))
