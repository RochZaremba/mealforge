"""Validate bookmark shape without resolving, fetching or granting source rights.

This policy is deliberately not a transport/SSRF validator. A public-looking
DNS name may resolve to a private address; a future fetcher must independently
check rights, resolved addresses and every redirect.
"""

import re
import unicodedata
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import quote, urlsplit

MAX_URL_BYTES = 2048
INVALID_URL = "Podaj poprawny publiczny adres HTTPS przepisu."
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_NUMERIC_FINAL_LABEL = re.compile(r"(?:[0-9]+|0x[0-9a-f]*)\Z")
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
_ENCODED_CONTROL = re.compile(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", re.IGNORECASE)
_ENCODED_DOT = re.compile(r"%2e", re.IGNORECASE)
_PRIVATE_SUFFIXES = (
    "localhost", "local", "localdomain", "internal", "lan", "home",
    "home.arpa", "test", "invalid", "example", "onion",
)
_PATH_SAFE = "/:@!$&'()*+,;=-._~%"
_QUERY_SAFE = _PATH_SAFE + "?[]"


@dataclass(frozen=True, slots=True)
class ValidatedRecipeUrl:
    source_url: str
    canonical_url: str
    host: str


def _bounded_url(value: str) -> None:
    if not value or len(value.encode("utf-8")) > MAX_URL_BYTES:
        raise ValueError(INVALID_URL)


def _canonical_host(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.lower())
    if normalized.endswith("."):
        normalized = normalized[:-1]  # A single terminal DNS root dot is harmless.
    if not normalized or normalized.endswith(".") or "." not in normalized:
        raise ValueError(INVALID_URL)
    ascii_host = normalized.encode("idna").decode("ascii").lower()
    decoded = ascii_host.encode("ascii").decode("idna")
    if not normalized.isascii() and decoded != normalized:
        # Reject IDNA2003 mappings such as sharp-s, fullwidth and joiner removal.
        raise ValueError(INVALID_URL)
    if decoded.encode("idna").decode("ascii").lower() != ascii_host:
        raise ValueError(INVALID_URL)
    labels = ascii_host.split(".")
    if len(ascii_host) > 253 or any(_LABEL.fullmatch(label) is None for label in labels):
        raise ValueError(INVALID_URL)
    try:
        ip_address(ascii_host)
    except ValueError:
        pass
    else:
        raise ValueError(INVALID_URL)
    # WHATWG browsers recognize numeric final labels, including hex/octal and
    # shortened IPv4 forms which Python's strict ip_address intentionally rejects.
    if _NUMERIC_FINAL_LABEL.fullmatch(labels[-1]):
        raise ValueError(INVALID_URL)
    if any(ascii_host == suffix or ascii_host.endswith("." + suffix)
           for suffix in _PRIVATE_SUFFIXES):
        raise ValueError(INVALID_URL)
    return ascii_host


def validate_recipe_url(value: str) -> ValidatedRecipeUrl:
    """Return bounded opening/identity URLs, or one non-echoing Polish error."""
    try:
        if not isinstance(value, str):
            raise ValueError(INVALID_URL)
        _bounded_url(value)
        if any(char.isspace() or char == "\\"
               or unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
            raise ValueError(INVALID_URL)
        if _BAD_PERCENT.search(value) or _ENCODED_CONTROL.search(value):
            raise ValueError(INVALID_URL)
        parsed = urlsplit(value)
        if (parsed.scheme.lower() != "https" or not parsed.netloc
                or "@" in parsed.netloc or parsed.netloc.endswith(":")
                or parsed.port not in {None, 443} or parsed.hostname is None):
            raise ValueError(INVALID_URL)
        host = _canonical_host(parsed.hostname)
        if any(_ENCODED_DOT.sub(".", segment) in {".", ".."}
               for segment in parsed.path.split("/")):
            # Browsers remove these segments; rejecting avoids silently changing
            # a user's opening path while claiming to preserve it.
            raise ValueError(INVALID_URL)
        path = quote(parsed.path or "/", safe=_PATH_SAFE, encoding="utf-8", errors="strict")
        query = quote(parsed.query, safe=_QUERY_SAFE, encoding="utf-8", errors="strict")
        fragment = quote(parsed.fragment, safe=_QUERY_SAFE, encoding="utf-8", errors="strict")
        canonical = f"https://{host}{path}"
        if "?" in value.partition("#")[0]:
            canonical += "?" + query  # Preserve even an explicitly empty query.
        source = canonical + ("#" + fragment if "#" in value else "")
        _bounded_url(source)
        _bounded_url(canonical)
        return ValidatedRecipeUrl(source_url=source, canonical_url=canonical, host=host)
    except (ValueError, UnicodeError):
        raise ValueError(INVALID_URL) from None


def classify_source(host: str, registry: dict[str, Any]) -> str | None:
    """Match exact canonical domains only; never return permission or license."""
    try:
        canonical = _canonical_host(host)
    except (ValueError, UnicodeError):
        return None
    sources = registry.get("sources")
    if not isinstance(sources, list):
        return None
    matches: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id, domains = source.get("id"), source.get("domains")
        if not isinstance(source_id, str) or not source_id or not isinstance(domains, list):
            continue
        for domain in domains:
            if not isinstance(domain, str):
                continue
            try:
                if _canonical_host(domain) == canonical:
                    matches.add(source_id)
            except (ValueError, UnicodeError):
                continue
    # An ambiguous/malformed registry cannot silently pick a source's provenance.
    return next(iter(matches)) if len(matches) == 1 else None
