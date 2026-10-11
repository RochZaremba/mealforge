import json
import socket
import urllib.request
from dataclasses import FrozenInstanceError
from hashlib import sha256

import httpx
import pytest

from mealforge.importers.jsonld import parse_own_jsonld


def document(**changes: object) -> str:
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Moja receptura",
            "recipeIngredient": ["3 łyżki mąki", "woda według potrzeby"],
            "recipeInstructions": "Połącz własne składniki.",
            **changes,
        },
        ensure_ascii=False,
    )


@pytest.mark.parametrize(
    "type_name",
    ["Recipe", "https://schema.org/Recipe", "http://schema.org/Recipe", ["Thing", "Recipe"]],
)
@pytest.mark.parametrize("wrapper", ["direct", "list", "graph"])
def test_schema_shapes_preserve_literal_yield_sections_and_unknown_claims(type_name, wrapper):
    raw = document(
        **{
            "@type": type_name,
            "recipeYield": ["3 kg 700 g", "4 porcje"],
            "recipeInstructions": [
                {
                    "@type": "HowToSection",
                    "name": "Przygotowanie",
                    "itemListElement": [{"@type": "HowToStep", "text": "Mieszaj."}],
                }
            ],
            "nutrition": {"calories": "0 kcal"},
            "license": "CC0",
            "image": "http://127.0.0.1/",
            "author": "Niezweryfikowany autor",
            "suitableForDiet": "GlutenFreeDiet",
        }
    )
    if wrapper == "list":
        raw = "[" + raw + "]"
    elif wrapper == "graph":
        raw = '{"@context":"https://schema.org","@graph":[{"@type":"WebPage"},' + raw + "]}"
    result = parse_own_jsonld(raw)
    assert result.ingredients == ("3 łyżki mąki", "woda według potrzeby")
    assert result.recipe_yield_raw == ("3 kg 700 g", "4 porcje")
    assert result.instructions[0].section_path == ("Przygotowanie",)
    assert result.instructions[0].text == "Mieszaj."
    assert result.source_sha256 == sha256(raw.encode()).hexdigest()
    assert {"nutrition", "license", "image", "author", "suitableForDiet"} <= set(
        result.ignored_source_fields
    )
    with pytest.raises(FrozenInstanceError):
        result.title = "Zmiana"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "null",
        "true",
        "123",
        "{}",
        "[]",
        '<script type="application/ld+json">{}</script>',
        '{"name":"a","name":"b"}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        '{"x":1e999}',
        '{"x":' + "1" * 65 + "}",
        "[" * 33 + "0" + "]" * 33,
        "[" + ",".join(["0"] * 2048) + "]",
        '{"x":"\\ud800"}',
        '{"x":"\\udfff"}',
        document(name=" "),
        document(name="a" * 161),
        document(name="bad\x00title"),
        document(recipeIngredient=[]),
        document(recipeIngredient=["x"] * 41),
        document(recipeIngredient=[True]),
        document(recipeIngredient=["x" * 501]),
        document(recipeInstructions=[]),
        document(recipeInstructions=["x"] * 31),
        document(recipeInstructions={"@id": "https://source.invalid/step"}),
        document(recipeInstructions={"@type": "HowToStep", "name": "Name alone is not step text"}),
        document(recipeInstructions={"@type": "HowToSection", "name": "s", "itemListElement": []}),
        document(recipeYield={"@type": "QuantitativeValue", "value": 3700}),
        document(recipeYield=[]),
        document(recipeYield=True),
        document(recipeYield=["x"] * 9),
        document(extra="x" * 12289),
        "[" + document() + "," + document(name="Drugi") + "]",
    ],
)
def test_adversarial_inputs_fail_without_echo(raw):
    with pytest.raises(ValueError) as caught:
        parse_own_jsonld(raw)
    assert str(caught.value) == "Nieprawidłowy lub nieobsługiwany dokument własnego przepisu."


def test_quotes_and_brackets_in_literal_text_do_not_affect_depth():
    raw = document(recipeIngredient=['literal [ { " ' * 15], recipeYield=4)
    result = parse_own_jsonld(raw)
    assert result.recipe_yield_raw == ("4",)
    assert result.ingredients[0].startswith('literal [ { "')


def test_utf8_budget_applies_to_multibyte_input():
    raw = document(extra=["ą" * 3000, "ą" * 3000, "ą" * 1000])
    assert len(raw) < 12288 < len(raw.encode())
    with pytest.raises(ValueError):
        parse_own_jsonld(raw)


def test_remote_context_images_references_and_script_text_never_execute_or_fetch(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Parser attempted network or DNS")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(httpx, "get", forbidden)
    monkeypatch.setattr(httpx.Client, "request", forbidden)
    raw = document(
        **{
            "@context": "https://127.0.0.1/private",
            "image": "http://169.254.169.254/",
            "recipeInstructions": '<img src=x onerror="alert(1)"> pasteryzowane',
        }
    )
    assert parse_own_jsonld(raw).instructions[0].text.startswith("<img")
