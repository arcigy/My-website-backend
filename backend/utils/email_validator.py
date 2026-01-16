import re
import difflib
import dns.resolver

# Common email domains for typo suggestion
COMMON_DOMAINS = [
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com", 
    "outlook.com", "icloud.com", "aol.com", "protonmail.com", "zoho.com",
    # Slovak/local domains
    "azet.sk", "zoznam.sk", "centrum.sk", "post.sk", "pobox.sk", "atlas.sk", "gmail.sk"
]

def validate_email_deep(email: str, lang: str = "sk"):
    """
    Validates email format, checks for typos, and verifies MX records.
    Returns: (is_valid: bool, message: str, suggestion: str|None)
    """
    if not email:
        return False, "Email is empty" if lang != "sk" else "Email je prázdny", None

    # 1. Basic Syntax Check
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        msg = "Invalid email format." if lang != "sk" else "Neplatný formát e-mailu."
        return False, msg, None

    # 2. Extract Domain
    try:
        local_part, domain = email.rsplit('@', 1)
        domain = domain.lower()
    except ValueError:
        return False, "Invalid format" if lang != "sk" else "Neplatný formát", None

    # 3. Check for specific common typos
    if domain == "gmail.sk":
         suggestion_domain = "gmail.com"
         msg = f"Did you mean {local_part}@{suggestion_domain}?" if lang != "sk" else f"Mysleli ste {local_part}@{suggestion_domain}?"
         return False, "Email domain might be incorrect" if lang != "sk" else "Doména emailu môže byť nesprávna", f"{local_part}@{suggestion_domain}"

    # 4. Fuzzy Match for Typos
    if domain not in COMMON_DOMAINS:
        matches = difflib.get_close_matches(domain, COMMON_DOMAINS, n=1, cutoff=0.85)
        if matches:
            suggestion_domain = matches[0]
            suggestion = f"{local_part}@{suggestion_domain}"
            msg = "Did you mean...?" if lang != "sk" else "Mysleli ste...?"
            return False, msg, suggestion

    # 5. MX Record Check (DNS)
    try:
        # We only check likely external domains. localhost/internal skipped if any.
        records = dns.resolver.resolve(domain, 'MX')
        if not records:
             raise Exception("No MX records")
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, Exception) as e:
        # Fallback: try A record (some domains handle mail on A record, though rare for major ones)
        try:
             dns.resolver.resolve(domain, 'A')
        except:
             msg = "Domain does not exist." if lang != "sk" else "Doména neexistuje."
             return False, msg, None

    return True, "Valid", None
