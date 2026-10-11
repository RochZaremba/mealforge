import http.client
import json
import socket
import urllib.request
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from mealforge.importers.url_policy import (
    INVALID_URL,
    ValidatedRecipeUrl,
    classify_source,
    validate_recipe_url,
)


@pytest.mark.parametrize("supplied,opening,identity,host", [
    ("HTTPS://AniaGotuje.PL:443/przepis/zupa#skladniki",
     "https://aniagotuje.pl/przepis/zupa#skladniki",
     "https://aniagotuje.pl/przepis/zupa", "aniagotuje.pl"),
    ("https://example.com.", "https://example.com/", "https://example.com/", "example.com"),
    ("https://example.com/#", "https://example.com/#", "https://example.com/", "example.com"),
    ("https://example.com/?#", "https://example.com/?#", "https://example.com/?", "example.com"),
    ("https://example.com/a//b/%2F/%5C?q=2&q=1&x=%26#krok?1",
     "https://example.com/a//b/%2F/%5C?q=2&q=1&x=%26#krok?1",
     "https://example.com/a//b/%2F/%5C?q=2&q=1&x=%26", "example.com"),
    ("https://bücher.de/żurek?q=ą#część",
     "https://xn--bcher-kva.de/%C5%BCurek?q=%C4%85#cz%C4%99%C5%9B%C4%87",
     "https://xn--bcher-kva.de/%C5%BCurek?q=%C4%85", "xn--bcher-kva.de"),
    ("https://xn--bcher-kva.de/", "https://xn--bcher-kva.de/",
     "https://xn--bcher-kva.de/", "xn--bcher-kva.de"),
    ("https://bu\u0308cher.de/", "https://xn--bcher-kva.de/",
     "https://xn--bcher-kva.de/", "xn--bcher-kva.de"),
    ("https://example.com/a%2fb%5cc?second=2&first=1#x%23y",
     "https://example.com/a%2fb%5cc?second=2&first=1#x%23y",
     "https://example.com/a%2fb%5cc?second=2&first=1", "example.com"),
])
def test_opening_fragment_and_url_meaning_are_preserved(
    supplied: str, opening: str, identity: str, host: str,
) -> None:
    result = validate_recipe_url(supplied)
    assert result == ValidatedRecipeUrl(opening, identity, host)
    assert validate_recipe_url(opening) == result


@pytest.mark.parametrize("value", [
    "", "http://example.com/", "javascript:alert(1)", "data:text/html,test",
    "//example.com/", "https:example.com/", "https:///example.com/",
    "https://user@example.com/", "https://user:password@example.com/",
    "https://@example.com/", "https://example.com:80/", "https://example.com:444/",
    "https://example.com:/", "https://example.com:65536/", "https://example.com:bad/",
    "https://example.com\\@127.0.0.1/", "https://example.com/a\\b",
    " https://example.com/", "https://example.com/ ", "https://example.com/a b",
    "https://example.com/a\nb", "https://example.com/\t", "https://example.com/\x00",
    "https://example.com/\x7f", "https://example.com/\u202e", "https://example.com/\ud800",
    "https://example.com/%", "https://example.com/%2", "https://example.com/%GG",
    "https://example.com/%0a", "https://example.com/?q=%00", "https://example.com/#%7F",
    "https://127.0.0.1/", "https://[::1]/", "https://[2001:4860:4860::8888]/",
    "https://127.1/", "https://2130706433/", "https://0x7f000001/",
    "https://0177.0.0.1/", "https://127.0x1/", "https://1.2.3.999/",
    "https://0x.0x/", "https://example.0x/",
    "https://localhost/", "https://a.localhost/", "https://a.local/",
    "https://a.internal/", "https://a.test/", "https://a.invalid/", "https://a.onion/",
    "https://a.home.arpa/", "https://singlelabel/", "https://example..com/",
    "https://example.com../", "https://.example.com/", "https://-a.example.com/",
    "https://a-.example.com/", "https://under_score.example.com/",
    "https://%65xample.com/", "https://faß.de/", "https://ｅxample.com/",
    "https://x\u200dy.com/", "https://xn--zca.de/", "https://xn--.de/",
    "https://example\u3002com/", "https://example.com/./a", "https://example.com/a/../b",
    "https://example.com/%2e/", "https://example.com/a/.%2E/b",
    "https://example.com/%2E%2e/", "https://example.com/a/%2e./",
])
def test_hostile_urls_are_rejected_without_echoing_private_input(value: str) -> None:
    with pytest.raises(ValueError) as caught:
        validate_recipe_url(value)
    assert str(caught.value) == INVALID_URL


def test_dns_label_and_both_encoded_url_byte_budgets() -> None:
    prefix = "https://example.com/"
    at_limit = prefix + "a" * (2048 - len(prefix))
    assert len(validate_recipe_url(at_limit).source_url.encode()) == 2048
    for value in [at_limit + "a", at_limit + "#", prefix + "ą" * 400,
                  "https://" + "a" * 64 + ".com/",
                  "https://" + ".".join(["a" * 63] * 4) + "/"]:
        with pytest.raises(ValueError, match=INVALID_URL):
            validate_recipe_url(value)
    result = validate_recipe_url(prefix + "ą" * 200)
    assert "%C4%85" in result.source_url


def test_url_result_is_immutable() -> None:
    result = validate_recipe_url("https://example.com/")
    with pytest.raises(FrozenInstanceError):
        result.source_url = "https://other.example.com/"


def test_shape_validation_does_not_claim_a_public_resolved_address() -> None:
    # This syntactically public name can map to loopback. We neither resolve it
    # nor claim that saving a bookmark permits a server-side fetch.
    result = validate_recipe_url("https://127.0.0.1.nip.io/recipe")
    assert result.host == "127.0.0.1.nip.io"


@pytest.mark.parametrize("value", [None, True, 123, b"https://example.com/"])
def test_non_string_runtime_input_uses_the_same_generic_error(value: Any) -> None:
    with pytest.raises(ValueError, match=INVALID_URL):
        validate_recipe_url(value)


def test_registry_classification_is_exact_and_confers_no_rights() -> None:
    registry = json.loads(
        (Path(__file__).resolve().parents[3] / "config/recipe_sources.json").read_text()
    )
    for host, expected in [("mealime.com", "mealime"), ("www.aniagotuje.pl", "aniagotuje"),
                           ("www.kwestiasmaku.com", "kwestiasmaku"),
                           ("api.nal.usda.gov", "usda_fdc"),
                           ("MEALIME.COM.", "mealime"),
                           ("mealime.com.example.com", None), ("fake-mealime.com", None),
                           ("sub.aniagotuje.pl", None), ("unknown.example.com", None)]:
        assert classify_source(host, registry) == expected
    assert classify_source("mealime.com", {"sources": [
        {"id": "a", "domains": ["mealime.com"]},
        {"id": "b", "domains": ["mealime.com"]},
    ]}) is None
    assert classify_source("bücher.de", {"sources": [
        {"id": "book", "domains": ["xn--bcher-kva.de."]},
    ]}) == "book"
    assert classify_source("example.com", {"sources": [None, {}, {"domains": "example.com"}]}) \
        is None


def test_bookmark_validation_and_classification_never_resolve_or_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        calls.append("network")
        raise AssertionError("Bookmark policy attempted network access")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket, "gethostbyname", forbidden)
    monkeypatch.setattr(socket, "gethostbyname_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(http.client.HTTPConnection, "connect", forbidden)
    registry = {"sources": [{"id": "known", "domains": ["mealime.com"],
                             "automatic_fetch_enabled": True, "access_mode": "authorized_api",
                             "license": "CC0"}]}
    for value in ["https://mealime.com/recipes", "https://aniagotuje.pl/przepis/zupa",
                  "https://kwestiasmaku.com/", "https://unknown.example.com/",
                  "https://127.1/", "https://example.com/%0a"]:
        try:
            result = validate_recipe_url(value)
        except ValueError:
            continue
        source_id = classify_source(result.host, registry)
        assert source_id in {"known", None}
    assert calls == []
