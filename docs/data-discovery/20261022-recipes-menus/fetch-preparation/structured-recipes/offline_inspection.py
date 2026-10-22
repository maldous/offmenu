"""Conservative, non-executing inspection of already supplied small JSON records."""
import re
from urllib.parse import urlsplit

MAX_TEXT_CHARS = 200_000


def inspect_foodista_record(record):
    metadata = record.get("metadata")
    text = record.get("text")
    if not isinstance(metadata, dict) or not isinstance(text, str) or len(text) > MAX_TEXT_CHARS:
        raise ValueError("Invalid/bounded record required")
    url = metadata.get("url", "")
    if not isinstance(url, str):
        raise ValueError("URL must be text")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"foodista.com", "www.foodista.com"}:
        raise ValueError("Not an approved source host")
    if parsed.username or parsed.password or not parsed.path.startswith("/recipe/"):
        raise ValueError("Not a recipe path")
    text = text.replace("\r\n", "\n")
    body = re.split(r"(?m)^Comments:\s*$", text, maxsplit=1)[0]
    starts = list(re.finditer(r"(?m)^Ingredients\s*$", body))
    steps = list(re.finditer(r"(?m)^Preparation\s*$", body))
    if len(starts) != 1 or len(steps) != 1 or starts[0].end() >= steps[0].start():
        raise ValueError("Ambiguous or missing recipe sections")
    ingredients = body[starts[0].end():steps[0].start()].strip()
    instructions = re.split(r"(?m)^(?:About|Tools|Information)\s*$", body[steps[0].end():], maxsplit=1)[0].strip()
    title = body.splitlines()[0].strip() if body else ""
    if not title or not ingredients or not instructions:
        raise ValueError("Incomplete recipe")
    return {
        "status": "candidate_not_accepted", "source_id": record.get("id"),
        "source_url": url, "title_raw": title, "ingredients_raw": ingredients,
        "instructions_raw": instructions, "license_raw": metadata.get("license"),
        "authors_raw": metadata.get("authors"), "author_roles_verified": False,
        "created_raw": record.get("created"), "rights_approved": False,
    }


def inspect_themealdb_record(record):
    title, instructions = record.get("strMeal"), record.get("strInstructions")
    if not isinstance(title, str) or not title.strip() or not isinstance(instructions, str) or not instructions.strip():
        raise ValueError("Title and instructions required")
    if len(instructions) > MAX_TEXT_CHARS:
        raise ValueError("Oversized instruction text")
    ingredients = []
    for i in range(1, 21):
        name, measure = record.get(f"strIngredient{i}"), record.get(f"strMeasure{i}")
        if name is not None and not isinstance(name, str):
            raise ValueError("Ingredient names must be strings or null")
        if measure is not None and not isinstance(measure, str):
            raise ValueError("Measures must be strings or null")
        if name and name.strip():
            ingredients.append({"slot": i, "name_raw": name, "measure_raw": measure})
        elif measure and measure.strip():
            raise ValueError("Orphaned quantity without ingredient")
    if not ingredients:
        raise ValueError("Ingredients required")
    return {
        "status": "candidate_not_accepted", "source_id": record.get("idMeal"),
        "title_raw": title, "instructions_raw": instructions,
        "ingredients_raw": ingredients, "source_url": record.get("strSource"),
        "cc_confirmation_raw": record.get("strCreativeCommonsConfirmed"),
        "rights_approved": False,
    }
