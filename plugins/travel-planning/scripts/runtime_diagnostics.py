"""Categorize provider failures without returning upstream diagnostic text."""

from __future__ import annotations


MESSAGES = {
    "authorization_failed": "Provider authorization failed; check the configured credential and access rights.",
    "quota_exceeded": "Provider quota or rate limit was exceeded; check account limits before retrying.",
    "runtime_unavailable": "Provider runtime or connection is unavailable; check installation and service status.",
    "provider_error": "Provider request failed; upstream diagnostic text was withheld.",
    "unavailable": "Source is unavailable; check configuration and provider status.",
}


def failure_message(kind: str) -> str:
    return MESSAGES.get(kind, MESSAGES["provider_error"])


def classify_failure(message: str) -> str:
    """Use a bounded sample only to select a fixed diagnostic category."""
    lower = message[:4096].lower()
    if any(token in lower for token in ("401", "403", "api key", "apikey", "unauthorized")):
        return "authorization_failed"
    if any(token in lower for token in ("429", "quota", "rate limit", "too many requests")):
        return "quota_exceeded"
    if any(token in lower for token in ("not found", "enoent", "command not found")):
        return "runtime_unavailable"
    return "provider_error"


def http_failure(status: object) -> tuple[str, str]:
    if type(status) is not int or not 100 <= status <= 599:
        return "provider_error", failure_message("provider_error")
    kind = "authorization_failed" if status in {401, 403} else "quota_exceeded" if status == 429 else "provider_error"
    return kind, f"{failure_message(kind)} HTTP status {status}."
