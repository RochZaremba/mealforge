"""Bounded schema.org-shaped JSON preview, without JSON-LD expansion or any I/O."""

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Literal

MAX_DOCUMENT_BYTES = 12288
PARSER_VERSION: Literal["jsonld-preview-v1"] = "jsonld-preview-v1"


def invalid() -> ValueError:
    return ValueError("Nieprawidłowy lub nieobsługiwany dokument własnego przepisu.")


def bounded_depth(document: str) -> None:
    depth = 0
    quoted = False
    escaped = False
    for char in document:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 32:
                raise invalid()
        elif char in "]}":
            depth -= 1


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise invalid()
        result[key] = value
    return result


def number(token: str) -> Decimal:
    if len(token) > 64:
        raise invalid()
    try:
        value = Decimal(token)
    except InvalidOperation:
        raise invalid() from None
    if not value.is_finite() or abs(value.adjusted()) > 100:
        raise invalid()
    return value


def reject_constant(_: str) -> None:
    raise invalid()


def literal(value: Any, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise invalid()
    if any((ord(char) < 32 and char not in "\n\t") or ord(char) == 127 for char in value):
        raise invalid()
    return value


def has_type(node: dict[str, Any], name: str) -> bool:
    types = node.get("@type")
    if not isinstance(types, list):
        types = [types]
    allowed = {name, f"https://schema.org/{name}", f"http://schema.org/{name}"}
    return any(isinstance(value, str) and value in allowed for value in types)


@dataclass(frozen=True)
class ParsedStep:
    text: str
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class ParsedRecipe:
    title: str
    ingredients: tuple[str, ...]
    instructions: tuple[ParsedStep, ...]
    recipe_yield_raw: tuple[str, ...]
    source_sha256: str
    ignored_source_fields: tuple[str, ...]


def parse_own_jsonld(document: str) -> ParsedRecipe:
    try:
        if len(document.encode("utf-8")) > MAX_DOCUMENT_BYTES:
            raise invalid()
        bounded_depth(document)
        root = json.loads(
            document,
            object_pairs_hook=unique_object,
            parse_int=number,
            parse_float=number,
            parse_constant=reject_constant,
        )
        if not isinstance(root, (dict, list)):
            raise invalid()
        stack = [root]
        candidates: list[dict[str, Any]] = []
        count = 0
        while stack:
            node = stack.pop()
            count += 1
            if count > 2048:
                raise invalid()
            if isinstance(node, dict):
                if has_type(node, "Recipe"):
                    candidates.append(node)
                stack.extend(node.keys())
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, str):
                node.encode("utf-8")  # Reject escaped lone surrogates even in ignored fields.
                if len(node) > 4096:
                    raise invalid()
        if len(candidates) != 1:
            raise invalid()
        recipe = candidates[0]
        title = literal(recipe.get("name"), 160)
        ingredients = recipe.get("recipeIngredient")
        if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 40:
            raise invalid()
        texts = tuple(literal(item) for item in ingredients)
        steps: list[ParsedStep] = []

        def instructions(value: Any, sections: tuple[str, ...] = ()) -> None:
            if isinstance(value, list):
                if not value:
                    raise invalid()
                for item in value:
                    instructions(item, sections)
                return
            if isinstance(value, dict):
                if has_type(value, "HowToSection"):
                    name = literal(value.get("name"), 160)
                    if len(sections) >= 8:
                        raise invalid()
                    instructions(value.get("itemListElement"), (*sections, name))
                    return
                if not has_type(value, "HowToStep"):
                    raise invalid()
                value = value.get("text")
            steps.append(ParsedStep(literal(value), sections))
            if len(steps) > 30:
                raise invalid()

        instructions(recipe.get("recipeInstructions"))
        raw_yield = recipe.get("recipeYield")
        yields: tuple[str, ...] = ()
        if raw_yield is not None:
            values = raw_yield if isinstance(raw_yield, list) else [raw_yield]
            if not 1 <= len(values) <= 8:
                raise invalid()
            yields = tuple(
                literal(str(value) if isinstance(value, Decimal) else value) for value in values
            )
        ignored = tuple(
            key
            for key in (
                "@context",
                "@id",
                "url",
                "image",
                "author",
                "license",
                "nutrition",
                "prepTime",
                "cookTime",
                "totalTime",
                "suitableForDiet",
                "storageMethod",
            )
            if key in recipe or key == "@context" and isinstance(root, dict) and key in root
        )
        return ParsedRecipe(
            title,
            texts,
            tuple(steps),
            yields,
            sha256(document.encode("utf-8")).hexdigest(),
            ignored,
        )
    except (ValueError, TypeError, UnicodeError, RecursionError, InvalidOperation):
        raise invalid() from None
