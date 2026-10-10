"""Verify original recipe unknowns and the installed/runtime seed asset."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from decimal import Decimal, InvalidOperation
from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 65_536
NUTRIENTS = {"kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def decode(raw: bytes) -> dict:
    require(len(raw) <= MAX_BYTES, "Fixture przekracza limit rozmiaru.")
    value = json.loads(raw)
    require(isinstance(value, dict), "Fixture musi być obiektem JSON.")
    return value


def digest(value: dict) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def unknown_nutrients(row: dict) -> None:
    require(row.get("nutrient_provenance") is None, "Nieznana proweniencja nie może być wymyślona.")
    require(row.get("allergen_status") == "unknown", "Alergeny wymagają weryfikacji.")
    nutrients = row.get("nutrients", row.get("nutrients_per_100g"))
    require(isinstance(nutrients, dict) and set(nutrients) == NUTRIENTS, "Niepełny kontrakt nutrient.")
    require(all(value is None for value in nutrients.values()), "Unknown nie może być zerem.")


def validate(value: dict) -> None:
    require(value.get("fixture_only") is True, "Fixture musi być jawnie demonstracyjny.")
    recipes = value.get("recipes")
    require(isinstance(recipes, list) and len(recipes) == 3, "Wymagane trzy oryginalne szkice.")
    count = 0
    ids = set()
    for recipe in recipes:
        require(isinstance(recipe, dict), "Przepis musi być obiektem JSON.")
        require(recipe["id"] not in ids, "Powtórzony identyfikator fixture.")
        ids.add(recipe["id"])
        require(recipe["source_mode"] == "user_authored" and recipe["source_url"] is None,
                "Fixture nie może aktywować źródła sieciowego.")
        require(recipe["validation_status"] == "draft_requires_review", "To nie jest validated recipe.")
        provenance = recipe["provenance"]
        require(isinstance(provenance, dict), "Brak obiektu proweniencji.")
        require(provenance["source_id"] == "original_fixture" and provenance["author"] == "MealForge",
                "Brak identyfikowalnego autorstwa.")
        require(provenance["license"] == "CC0-1.0"
                and provenance["license_scope"] == "original_recipe_text", "Nieprawidłowy zakres praw.")
        require(recipe["servings"] == 2 and recipe["servings_basis"] == "intentional_recipe_design",
                "Liczba porcji to deklaracja projektu, nie obliczenie kalorii.")
        require(recipe["yield_basis"] == "unknown_until_weighed_after_cooking", "Uzysk wymaga ważenia.")
        for name in ("yield_mass_g", "storage_method", "storage_validation_ref", "price",
                     "prep_time_min", "cook_time_min"):
            require(recipe[name] is None, "Nie wolno wymyślać uzysku, przechowywania, cen ani czasu.")
        unknown_nutrients(recipe)
        for ingredient in recipe["ingredients"]:
            require(isinstance(ingredient, dict), "Składnik musi być obiektem JSON.")
            count += 1
            require(isinstance(ingredient["amount"], str), "Gramatury fixture wymagają Decimal string.")
            amount = Decimal(ingredient["amount"])
            require(amount.is_finite() and 0 < amount <= Decimal("999999.999")
                    and amount.as_tuple().exponent >= -3, "Nieprawidłowa dokładna ilość.")
            require(ingredient["unit"] == "g", "Fixture deklaruje gramy, bez konwersji jednostek.")
            require(ingredient["raw_or_cooked"] in {"raw", "cooked", "as_packaged", "unknown"},
                    "Nieprawidłowy stan składnika.")
            unknown_nutrients(ingredient)
    require(count == 13, "Wymagane trzynaście oryginalnych ilości składników.")


def check_docker(expected: str) -> None:
    program = (
        "import hashlib,json; from importlib.resources import files; "
        "raw=files('mealforge.recipes').joinpath('originals.json').read_bytes(); "
        "assert len(raw)<=65536; "
        "value=json.loads(raw); "
        "print(hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,"
        "separators=(',',':')).encode()).hexdigest())"
    )
    result = subprocess.run(
        ["docker", "compose", "--env-file", ".env", "-f", "compose.dev.yml", "exec", "-T",
         "api", "/app/.venv/bin/python", "-c", program],
        cwd=ROOT, capture_output=True, timeout=30, check=False,
    )
    require(result.returncode == 0, "Brak poprawnego fixture w rzeczywistym kontenerze API.")
    require(result.stdout.decode().strip() == expected, "Runtime Docker fixture różni się od repo.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true", help="Also verify the running API container")
    args = parser.parse_args()
    try:
        expected = decode((ROOT / "fixtures/original-recipes.json").read_bytes())
        validate(expected)
        installed = decode(files("mealforge.recipes").joinpath("originals.json").read_bytes())
        require(installed == expected, "Zainstalowany fixture różni się od repozytorium.")
        if args.docker:
            check_docker(digest(expected))
    except (ValueError, KeyError, TypeError, InvalidOperation, OSError, ImportError,
            subprocess.TimeoutExpired):
        print("FAIL: fixture oryginalnych przepisów jest niekompletny, zmieniony lub niedostępny.")
        return 1
    print("PASS: trzy oryginalne szkice / trzynaście dokładnych ilości; unknown i prawa zachowane; "
          "zainstalowany fixture zgodny" + (" również w Docker." if args.docker else "."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
