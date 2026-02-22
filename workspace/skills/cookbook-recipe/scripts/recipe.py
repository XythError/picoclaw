#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".picoclaw" / "workspace"
RECIPES_DIR = WORKSPACE / "cloud" / "Rezepte"
TEMPLATE_FILE = Path(__file__).resolve().parent.parent / "assets" / "recipe-template.json"


def emit_ok(**kwargs):
    payload = {"ok": True}
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0)


def emit_error(code, message, exit_code=1, **kwargs):
    payload = {"ok": False, "error": {"code": code, "message": message}}
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(exit_code)


def slugify(text):
    text = text.strip().lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "rezept"


def load_template():
    if TEMPLATE_FILE.exists():
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "",
        "description": "",
        "image": "full.jpg",
        "author": {"@type": "Person", "name": "PicoClaw"},
        "datePublished": datetime.now().strftime("%Y-%m-%d"),
        "prepTime": "PT20M",
        "cookTime": "PT30M",
        "totalTime": "PT50M",
        "recipeYield": "2 Portionen",
        "recipeCategory": "Hauptgericht",
        "recipeCuisine": "International",
        "recipeIngredient": [],
        "recipeInstructions": [],
    }


def cmd_create(args):
    if not args.name:
        emit_error("missing_name", "--name ist erforderlich")

    slug = args.slug or slugify(args.name)
    recipe_dir = RECIPES_DIR / slug
    recipe_dir.mkdir(parents=True, exist_ok=True)

    recipe = load_template()
    recipe["name"] = args.name
    recipe["description"] = args.description or recipe.get("description", "")
    recipe["image"] = "full.jpg"
    recipe["datePublished"] = datetime.now().strftime("%Y-%m-%d")

    if args.category:
        recipe["recipeCategory"] = args.category
    if args.cuisine:
        recipe["recipeCuisine"] = args.cuisine
    if args.yield_text:
        recipe["recipeYield"] = args.yield_text
    if args.prep_time:
        recipe["prepTime"] = args.prep_time
    if args.cook_time:
        recipe["cookTime"] = args.cook_time
    if args.total_time:
        recipe["totalTime"] = args.total_time

    if args.ingredient:
        recipe["recipeIngredient"] = args.ingredient
    if args.step:
        recipe["recipeInstructions"] = [{"@type": "HowToStep", "text": step} for step in args.step]

    if not recipe.get("recipeIngredient"):
        emit_error("missing_ingredients", "Mindestens eine --ingredient ist erforderlich")
    if not recipe.get("recipeInstructions"):
        emit_error("missing_steps", "Mindestens ein --step ist erforderlich")

    recipe_file = recipe_dir / "recipe.json"
    with open(recipe_file, "w", encoding="utf-8") as f:
        json.dump(recipe, f, indent=2, ensure_ascii=False)

    image_file = recipe_dir / "full.jpg"
    image_result = {"downloaded": False, "path": str(image_file)}
    if args.image_url:
        try:
            request = urllib.request.Request(
                args.image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            with open(image_file, "wb") as f:
                f.write(data)
            image_result["downloaded"] = True
            image_result["bytes"] = len(data)
        except Exception as e:
            emit_error("image_download_failed", str(e), recipe_dir=str(recipe_dir))

    emit_ok(
        command="create",
        slug=slug,
        recipe_dir=str(recipe_dir),
        recipe_file=str(recipe_file),
        image=image_result,
    )


def cmd_validate(args):
    slug = args.slug
    recipe_dir = RECIPES_DIR / slug
    recipe_file = recipe_dir / "recipe.json"
    image_file = recipe_dir / "full.jpg"

    if not recipe_dir.exists():
        emit_error("missing_recipe_dir", f"Rezeptordner fehlt: {recipe_dir}")
    if not recipe_file.exists():
        emit_error("missing_recipe_json", f"recipe.json fehlt: {recipe_file}")
    if not image_file.exists():
        emit_error("missing_full_jpg", f"full.jpg fehlt: {image_file}")

    with open(recipe_file, "r", encoding="utf-8") as f:
        recipe = json.load(f)

    required = ["name", "recipeIngredient", "recipeInstructions"]
    missing = [k for k in required if not recipe.get(k)]
    if missing:
        emit_error("missing_fields", f"Pflichtfelder fehlen: {missing}")

    if recipe.get("image") != "full.jpg":
        emit_error("invalid_image_field", "recipe.json muss image=full.jpg setzen")

    emit_ok(
        command="validate",
        slug=slug,
        recipe_dir=str(recipe_dir),
        files=[str(recipe_file), str(image_file)],
    )


def cmd_sync(_args):
    script = WORKSPACE / "nextcloud" / "nextcloud-sync.sh"
    if not script.exists():
        emit_error("missing_sync_script", f"Sync-Script fehlt: {script}")

    result = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE),
    )

    if result.returncode != 0:
        emit_error(
            "sync_failed",
            (result.stderr or result.stdout or "Unbekannter Fehler").strip(),
            returncode=result.returncode,
        )

    emit_ok(
        command="sync",
        message="Nextcloud-Sync erfolgreich",
        output=(result.stdout or "").strip(),
    )


def build_parser():
    parser = argparse.ArgumentParser(description="Cookbook Recipe CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Rezept anlegen")
    p_create.add_argument("--name", required=True, help="Rezeptname")
    p_create.add_argument("--slug", help="Optionaler Slug")
    p_create.add_argument("--description", default="", help="Beschreibung")
    p_create.add_argument("--category", default="", help="Kategorie")
    p_create.add_argument("--cuisine", default="", help="Kueche")
    p_create.add_argument("--yield", dest="yield_text", default="", help="Portionen")
    p_create.add_argument("--prep-time", default="", help="ISO8601, z.B. PT20M")
    p_create.add_argument("--cook-time", default="", help="ISO8601, z.B. PT45M")
    p_create.add_argument("--total-time", default="", help="ISO8601, z.B. PT65M")
    p_create.add_argument("--ingredient", action="append", help="Kann mehrfach verwendet werden")
    p_create.add_argument("--step", action="append", help="Kann mehrfach verwendet werden")
    p_create.add_argument("--image-url", default="", help="Optionales Rezeptbild (wird als full.jpg gespeichert)")

    p_validate = sub.add_parser("validate", help="Rezept validieren")
    p_validate.add_argument("--slug", required=True, help="Rezept-Slug")

    sub.add_parser("sync", help="Nextcloud Sync ausfuehren")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "sync":
        cmd_sync(args)


if __name__ == "__main__":
    main()
