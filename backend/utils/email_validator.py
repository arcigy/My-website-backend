import re
import difflib

# Common email domains for typo suggestion
COMMON_DOMAINS = [
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com", 
    "outlook.com", "icloud.com", "aol.com", "protonmail.com", "zoho.com",
    # Slovak/local domains
    "azet.sk", "zoznam.sk", "centrum.sk", "post.sk", "pobox.sk", "atlas.sk", "gmail.sk"
]

def validate_email_deep(email: str, lang: str = "sk"):
    """
    Validates email format and checks for typos in the domain.
    Returns: (is_valid: bool, message: str, suggestion: str|None)
    """
    if not email:
        return False, "Email is empty" if lang != "sk" else "Email je prázdny", None

    # 1. Basic Syntax Check
    # Must have @, dot, and no spaces
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        msg = "Invalid email format." if lang != "sk" else "Neplatný formát e-mailu."
        return False, msg, None

    # 2. Extract Domain
    try:
        local_part, domain = email.rsplit('@', 1)
        domain = domain.lower()
    except ValueError:
        return False, "Invalid format" if lang != "sk" else "Neplatný formát", None

    # 3. Check for specific typo: gmail.sk -> gmail.com logic requested by user?
    # Actually user said "how gmail.sk should look". 
    # Usually gmail.sk redirects to gmail.com, but let's treat it as a potential typo if they meant .com
    # But wait, gmail.sk is NOT a valid email provider (Google owns it but doesn't issue emails there).
    if domain == "gmail.sk":
         suggestion_domain = "gmail.com"
         msg = f"Did you mean {local_part}@{suggestion_domain}?" if lang != "sk" else f"Mysleli ste {local_part}@{suggestion_domain}?"
         return False, "Email domain might be incorrect" if lang != "sk" else "Doména emailu môže byť nesprávna", f"{local_part}@{suggestion_domain}"

    # 4. Fuzzy Match for Typos
    # Use difflib to find close matches in COMMON_DOMAINS
    # Only if the domain is NOT in COMMON_DOMAINS
    if domain not in COMMON_DOMAINS:
        matches = difflib.get_close_matches(domain, COMMON_DOMAINS, n=1, cutoff=0.85)
        if matches:
            suggestion_domain = matches[0]
            # Verify it's not just a subdomain or completely different valid domain
            # Heuristic: if distance is small
             
            suggestion = f"{local_part}@{suggestion_domain}"
            msg = "Did you mean...?" if lang != "sk" else "Mysleli ste...?"
            # We return Valid=False so the UI shows the error/suggestion
            return False, msg, suggestion

    # 5. MX Record Check (Optional - requires dnspython, might fail on some envs)
    # Skipping to keep it simple and robust for this environment.
    
    return True, "Valid", None
