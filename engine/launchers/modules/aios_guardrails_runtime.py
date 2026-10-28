"""
AIOS Guardrails Runtime - Track E2 (hardened)
Replaces the stub. Detects prompt injection patterns and
dangerous content in text (not commands).
"""
import re

# Prompt injection signals
_INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions", "high"),
    (r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|rules)", "high"),
    (r"you\s+are\s+now\s+(?:in\s+)?(?:developer|admin|root|god)\s+mode", "high"),
    (r"print\s+(?:your|the)\s+(?:system\s+)?prompt", "high"),
    (r"reveal\s+(?:your|the)\s+(?:system\s+)?prompt", "high"),
    (r"what\s+is\s+your\s+(?:system\s+)?prompt", "medium"),
    (r"forget\s+(?:all\s+)?(?:previous|prior|earlier)", "high"),
    (r"new\s+instructions?\s*:", "medium"),
    (r"system\s*:\s*", "medium"),
    (r"<\|im_start\|>", "high"),
    (r"\[INST\]", "high"),
    (r"<\|system\|>", "high"),
]

def check_safety(text):
    """Assess text for prompt-injection risk."""
    if text is None or str(text).strip() == "":
        return {"safe": True, "risk": "low", "reason": "empty"}
    
    text_str = str(text)
    text_lower = text_str.lower()
    
    max_risk = "low"
    matched = None
    
    for pattern, risk in _INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if risk == "high":
                return {
                    "safe": False,
                    "risk": "high",
                    "reason": f"prompt injection pattern: {pattern[:40]}"
                }
            elif risk == "medium" and max_risk == "low":
                max_risk = "medium"
                matched = pattern
    
    return {
        "safe": max_risk in ("low",),
        "risk": max_risk,
        "reason": matched or "passed"
    }
