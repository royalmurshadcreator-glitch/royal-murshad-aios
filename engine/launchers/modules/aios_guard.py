"""
AIOS Safety Guard - Track E2 (hardened)
Replaces the trivial 6-string blocklist with a robust denylist
that detects command chaining, shell meta-operators, and dangerous
Windows/POSIX commands.
"""
import re

# Risk levels
LOW      = "low"
MEDIUM   = "medium"
HIGH     = "high"
CRITICAL = "critical"

# Dangerous patterns (case-insensitive regex)
_DANGEROUS_PATTERNS = [
    # Destructive file operations
    (r"\brm\s+-(?:rf|fr)\s+(?:/|\*|[a-z]:\\)", CRITICAL),
    (r"\brm\s+-r\s+", CRITICAL),
    (r"\bformat\s+[a-z]:", CRITICAL),
    (r"\brd\s+/s\s+/q\s+[a-z]:", CRITICAL),
    (r"\bdel\s+/f\s+/s\s+/q\s+[a-z]:\\\*", CRITICAL),
    (r"\bRemove-Item\s+.*-Recurse.*-Force", CRITICAL),
    (r"\bmkfs\b", CRITICAL),
    (r"\bdd\s+if=.*of=/dev/", CRITICAL),
    (r":\(\)\s*\{\s*:\|:&\s*\}", CRITICAL),  # fork bomb

    # System state changes
    (r"\bshutdown\s+/[sr]", CRITICAL),
    (r"\bformat\s+", HIGH),
    (r"\bdiskpart\b", CRITICAL),

    # Privilege escalation
    (r"\bnet\s+user\s+\w+\s+/add", HIGH),
    (r"\bnet\s+localgroup\s+administrators", HIGH),
    (r"\breg\s+delete\b", HIGH),
    (r"\btaskkill\s+/f\s+/im\s+\*", HIGH),

    # Remote code execution
    (r"curl\s+[^|]+\|\s*(?:sh|bash|powershell)", CRITICAL),
    (r"wget\s+[^|]+\|\s*(?:sh|bash)", CRITICAL),
    (r"iex\s*\(.*Invoke-WebRequest", CRITICAL),
    (r"\bpowershell\s+-enc\s+", HIGH),
    (r"\bbase64\s+-d\s*\|", HIGH),
]

# Shell meta-operators that indicate chaining
_CHAINING_PATTERNS = [
    (r"&&",   HIGH),   # command chaining
    (r"\|\|", HIGH),   # OR chaining
    (r";\s*\w", HIGH),  # semicolon chaining
    (r"\|",   MEDIUM),  # pipes (legitimate but risky)
    (r"`",    HIGH),   # backtick command substitution
    (r"\$\(", HIGH),   # $() command substitution
    (r">\s*[a-z]:\\", MEDIUM),  # file redirection to system drive
]

def check_command(cmd):
    """
    Check a command and return a risk assessment dict.
    Backward-compatible: also returns True/False as 'safe'.
    """
    if cmd is None or str(cmd).strip() == "":
        return {"safe": True, "risk": LOW, "reason": "empty"}
    
    cmd_str = str(cmd)
    cmd_lower = cmd_str.lower()
    
    # 1. Check dangerous patterns
    for pattern, risk in _DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return {
                "safe": False,
                "risk": risk,
                "reason": f"matched dangerous pattern: {pattern[:40]}"
            }
    
    # 2. Check chaining (may elevate risk even if individual commands are safe)
    max_risk = LOW
    for pattern, risk in _CHAINING_PATTERNS:
        if re.search(pattern, cmd_str):
            if risk == HIGH:
                return {
                    "safe": False,
                    "risk": HIGH,
                    "reason": f"shell meta-operator detected: {pattern}"
                }
            elif risk == MEDIUM and max_risk == LOW:
                max_risk = MEDIUM
    
    # 3. If multiple pipes (query string suspicion) -> medium
    pipe_count = cmd_str.count("|")
    if pipe_count >= 2:
        return {
            "safe": False,
            "risk": MEDIUM,
            "reason": f"multiple pipes ({pipe_count}) - potential chaining"
        }
    
    return {
        "safe": True,
        "risk": max_risk,
        "reason": "passed denylist and chaining checks"
    }


def check(cmd):
    """Legacy alias for check_command — returns bool."""
    return check_command(cmd).get("safe", False)

# ===== RMS SAFETY PATCH v3 (tuple form) =====
_DANGEROUS_PATTERNS = list(_DANGEROUS_PATTERNS) + [
    (r'(?<![&|])\s&\s(?![&|])', 'high'),
    (r'\s&&\s', 'high'),
    (r'\s\|\|\s', 'high'),
    (r'\bdel\s+/[sqf]', 'critical'),
    (r'\bformat\s+[a-z]:', 'critical'),
    (r'\bdiskpart\b', 'critical'),
    (r'\bbcdedit\b', 'critical'),
    (r'\bvssadmin\s+(?:delete|resize)', 'critical'),
    (r'\breg\s+delete\b', 'high'),
    (r'\bshutdown\s+/[rs]', 'critical'),
    (r'\bcipher\s+/w', 'high'),
    (r'\bnet\s+user\s+\S+\s+\S+\s+/add', 'high'),
    (r'\bcmd(?:\.exe)?\s+/c\b', 'high'),
    (r'\bpowershell(?:\.exe)?\s+-(?:c|command|enc|encodedcommand)\b', 'high'),
]
# ===== END SAFETY PATCH v3 =====
