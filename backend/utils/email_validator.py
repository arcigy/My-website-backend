import re
import socket
import dns.resolver

COMMON_TYPOS = {
    'gmaial.com': 'gmail.com',
    'gmal.com': 'gmail.com',
    'gamil.com': 'gmail.com',
    'gnail.com': 'gmail.com',
    'yaho.com': 'yahoo.com',
    'hotmal.com': 'hotmail.com',
    'outlok.com': 'outlook.com',
    'seznam.sk': 'seznam.cz', # Common error for Seznam
    'centrum.com': 'centrum.sk', # Common error in Slovakia
    'azet.com': 'azet.sk',
}

def validate_email_deep(email: str, lang: str = "sk"):
    """
    Returns (is_valid, message, suggestion)
    """
    email = email.strip().lower()
    
    messages = {
        "sk": {
            "invalid": "Neplatný formát e-mailu.",
            "suggestion": "Mysleli ste {suggestion}?",
            "no_domain": "Doména {domain} nebola nájdená.",
            "no_mx": "Doména {domain} neexistuje alebo nemá poštový server.",
            "unavailable": "Doména {domain} je nedostupná.",
            "valid": "E-mail je v poriadku."
        },
        "en": {
            "invalid": "Invalid email format.",
            "suggestion": "Did you mean {suggestion}?",
            "no_domain": "Domain {domain} was not found.",
            "no_mx": "Domain {domain} doesn't exist or has no mail server.",
            "unavailable": "Domain {domain} is unavailable.",
            "valid": "Email is valid."
        }
    }
    
    current_msg = messages.get(lang, messages["en"])
    
    # 1. Syntax Check
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return False, current_msg["invalid"], None
    
    parts = email.split('@')
    domain = parts[1]
    
    # 2. Typo Check
    if domain in COMMON_TYPOS:
        suggestion = f"{parts[0]}@{COMMON_TYPOS[domain]}"
        return False, current_msg["suggestion"].format(suggestion=suggestion), suggestion

    # 3. Domain Check (MX records)
    try:
        # Try to resolve MX records
        records = dns.resolver.resolve(domain, 'MX')
        if not records:
            return False, current_msg["no_mx"].format(domain=domain), None
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False, current_msg["no_domain"].format(domain=domain), None
    except Exception:
        # Fallback to A record check if MX fails or dns.resolver is not perfect
        try:
            socket.gethostbyname(domain)
        except:
            return False, current_msg["unavailable"].format(domain=domain), None

    return True, current_msg["valid"], None
