---
name: pollinations-ai
description: Bildgenerierung via Pollinations.ai API mit imagen-4 und flux. Standard-Bildgenerator fuer alle Bilder inkl. Rezepte.
---

# Pollinations.ai Bildgenerierung

Standard-Skill fuer alle Bildgenerierungen (Rezepte, Illustrationen, etc.).

## API

- **Endpunkt**: `https://gen.pollinations.ai/image/{prompt}?params`
- **API-Key**: Im Script hinterlegt (Bearer-Token)
- **Modell**: `imagen-4` (premium, 400/Tag), Fallback: `flux` (kostenlos)
- **Limit**: 400 Bilder pro Tag

## Script

```bash
# Bild generieren
python3 skills/pollinations-ai/scripts/pollinations.py generate "golden bread loaf on wooden table" --width 1024 --height 768

# Mit spezifischem Modell
python3 skills/pollinations-ai/scripts/pollinations.py generate "italian lasagna" --model flux --nologo

# Nur URL generieren (kein Download)
python3 skills/pollinations-ai/scripts/pollinations.py url "chocolate cake"

# API testen
python3 skills/pollinations-ai/scripts/pollinations.py test

# Verfuegbare Modelle
python3 skills/pollinations-ai/scripts/pollinations.py models
```

## Parameter

| Parameter   | Beschreibung                  | Default    |
|-------------|-------------------------------|------------|
| --model     | imagen-4, flux                | imagen-4   |
| --width     | Bildbreite in Pixeln          | 1024       |
| --height    | Bildhoehe in Pixeln           | 768        |
| --output    | Ausgabepfad                   | ~/name.jpg |
| --seed      | Seed fuer Reproduzierbarkeit  | zufaellig  |
| --nologo    | Kein Wasserzeichen            | aus        |
| --enhance   | KI-optimierter Prompt         | aus        |
| --json      | JSON-Ausgabe                  | aus        |

## Regeln

- IMMER englische Prompts verwenden
- Prompt so detailliert wie moeglich
- Bei Rezeptbildern: Zutaten, Anrichtung beschreiben
- Bei Rate-Limit (imagen-4): Automatischer Fallback auf flux
- `url` Subcommand fuer Markdown-Einbettung ohne Download
