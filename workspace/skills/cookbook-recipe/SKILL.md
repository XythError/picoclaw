---
name: cookbook-recipe
description: "Erstellt Nextcloud Cookbook-kompatible Rezepte im lokalen Spiegel (exaktes Format der Cookbook-App)."
---

# Nextcloud Cookbook Recipe Skill

Trigger: "erstelle ein Rezept fuer X", "neues Rezept Lasagne", etc.

## Nextcloud Cookbook Dateistruktur (WICHTIG!)

Die Nextcloud Cookbook-App erwartet pro Rezept einen Ordner mit:
- **recipe.json** (Pflicht)
- **full.jpg** (Pflicht fuer Bildanzeige)

FALSCH: `image.jpg`, `photo.jpg`, `bild.png`
RICHTIG: `full.jpg`

## Stable CLI (JSON-Contract)

Nutze **immer** das Script `scripts/recipe.py` statt ad-hoc Shell-Heredocs.

```bash
python3 skills/cookbook-recipe/scripts/recipe.py create ...
python3 skills/cookbook-recipe/scripts/recipe.py validate --slug <slug>
python3 skills/cookbook-recipe/scripts/recipe.py sync
```

Alle Befehle liefern JSON auf stdout und setzen Exit-Code `0` bei Erfolg, `1` bei Fehler.

## Workflow

### 1) Rezept anlegen

```bash
python3 skills/cookbook-recipe/scripts/recipe.py create \
  --name "Indisches Kichererbsen-Curry" \
  --description "Cremiges Curry mit Kokosmilch" \
  --category "Hauptgericht" \
  --cuisine "Indisch" \
  --yield "4 Portionen" \
  --prep-time PT20M \
  --cook-time PT30M \
  --total-time PT50M \
  --ingredient "2 Dosen Kichererbsen" \
  --ingredient "1 Zwiebel" \
  --step "Zwiebel anbraten" \
  --step "Gewuerze und Kichererbsen zugeben" \
  --image-url "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg"
```

### 2) Rezept validieren

```bash
python3 skills/cookbook-recipe/scripts/recipe.py validate --slug indisches-kichererbsen-curry
```

### 3) Nextcloud-Sync (Pflicht)

```bash
python3 skills/cookbook-recipe/scripts/recipe.py sync
```

## Regeln
- Keine Shell-Heredoc-Ketten als Primärweg
- Keine manuellen Dateinamen fuer das Bild: immer `full.jpg`
- Nach `create` immer `validate`, danach `sync`
