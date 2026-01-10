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

def validate_email_deep(email: str):
    """
    Returns (is_valid, message, suggestion)
    """
    email = email.strip().lower()
    
    # 1. Syntax Check
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return False, "Neplatný formát e-mailu.", None
    
    parts = email.split('@')
    domain = parts[1]
    
    # 2. Typo Check
    if domain in COMMON_TYPOS:
        suggestion = f"{parts[0]}@{COMMON_TYPOS[domain]}"
        return False, f"Mysleli ste {suggestion}?", suggestion

    # 3. Domain Check (MX records)
    try:
        # Try to resolve MX records
        records = dns.resolver.resolve(domain, 'MX')
        if not records:
            return False, f"Doména {domain} neexistuje alebo nemá poštový server.", None
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False, f"Doména {domain} nebola nájdená.", None
    except Exception:
        # Fallback to A record check if MX fails or dns.resolver is not perfect
        try:
            socket.gethostbyname(domain)
        except:
            return False, f"Doména {domain} je nedostupná.", None

    return True, "E-mail je v poriadku.", None
