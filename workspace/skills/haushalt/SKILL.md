---
name: haushalt
description: "Manage household tasks, shopping lists, cleaning schedules, and home inventory. Use when the user asks about household chores, grocery or shopping lists, cleaning plans, home maintenance reminders, or organizing household items."
metadata: {"nanobot":{"emoji":"🏠"}}
---

# Haushalt (Household Management)

Help organize and manage household tasks, lists, and schedules.

## Shopping & Grocery Lists

When creating or updating shopping lists:
- Group items by category (produce, dairy, bakery, frozen, household, etc.)
- Note quantities and units clearly (e.g., "2 kg Mehl", "1 L Milch")
- Mark recurring items as staples vs. one-time purchases
- Ask the user which store they're shopping at if relevant for brand/price advice

Example output format:
```
🛒 Einkaufsliste

🥦 Gemüse & Obst
  - Tomaten (500 g)
  - Bananen (1 Bund)
  - Karotten (1 kg)

🥛 Kühlwaren
  - Milch (1,5 L)
  - Butter (250 g)
  - Joghurt (4 Stk.)

🍞 Backwaren
  - Vollkornbrot (1 Laib)
  - Brötchen (6 Stk.)

🧴 Haushalt
  - Spülmittel
  - Küchenpapier (2 Rollen)
```

## Cleaning Schedules

When creating cleaning plans, organize by frequency:

**Daily (täglich):** Dishes, countertops, quick tidy

**Weekly (wöchentlich):** Vacuum, mop floors, bathrooms, laundry

**Monthly (monatlich):** Windows, refrigerator, oven, under furniture

**Seasonal / quarterly:** Declutter, deep clean, HVAC filters

Present as a checklist with checkboxes when possible.

## Home Maintenance Reminders

Common recurring maintenance tasks to suggest:
- HVAC filter replacement (every 1–3 months)
- Smoke detector battery check (annually)
- Gutter cleaning (spring and fall)
- Water heater check (annually)
- Refrigerator coil cleaning (twice a year)
- Chimney inspection (annually)
- Pest control (seasonally)

## Inventory Management

When tracking home inventory:
- Record item name, quantity, location, and purchase/expiry date
- Flag items running low (below minimum quantity)
- Suggest reorder when appropriate

Example inventory entry:
```
Item: Klopapier
Quantity: 4 Rollen
Location: Badezimmerschrank
Minimum: 6 (reorder when below)
Last purchased: 2024-01-15
```

## Language

Respond in the user's preferred language. This skill name is German but works in any language—follow the user's language in responses.
