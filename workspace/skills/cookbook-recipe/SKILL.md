---
name: cookbook-recipe
description: "Find, create, scale, and format cooking recipes. Use when the user asks for recipes, wants to scale ingredient quantities, substitute ingredients, plan meals, generate shopping lists from recipes, or get cooking instructions and tips."
metadata: {"nanobot":{"emoji":"🍳"}}
---

# Cookbook & Recipe Skill

Help with recipes, meal planning, and cooking guidance.

## Presenting Recipes

Always structure recipes with these sections:

```
# [Recipe Name]

**Prep time:** X min | **Cook time:** Y min | **Servings:** N

## Ingredients
- [quantity] [unit] [ingredient], [preparation note]

## Instructions
1. Step one.
2. Step two.

## Notes
- Substitutions, tips, storage instructions.
```

## Scaling Recipes

When asked to scale a recipe (e.g., "make it for 8 instead of 4"):
1. Calculate the scaling factor: `new_servings / original_servings`
2. Multiply all ingredient quantities by the factor
3. Keep cooking temperatures the same
4. Adjust cook time slightly for larger batches (note it in the recipe)
5. Round quantities to practical measures (e.g., 37.5 g → ~40 g)

## Ingredient Substitutions

Common substitutions to suggest:

| Original | Substitute |
|----------|-----------|
| Buttermilk (1 cup) | 1 cup milk + 1 tbsp lemon juice (wait 5 min) |
| Eggs (1 large) | 3 tbsp aquafaba, or 1 tbsp flaxseed + 3 tbsp water |
| All-purpose flour (1 cup) | 1 cup cake flour + 2 tsp cornstarch |
| Butter (1 cup) | ¾ cup vegetable oil, or 1 cup margarine |
| Brown sugar (1 cup) | 1 cup white sugar + 1 tbsp molasses |
| Sour cream | Equal amount plain Greek yogurt |
| Heavy cream | ¾ cup milk + ¼ cup melted butter |
| Wine (for cooking) | Equal amount broth + 1 tsp lemon juice |

## Dietary Adaptations

When adapting recipes for dietary restrictions:
- **Vegan**: Replace meat with legumes/tofu, dairy with plant-based alternatives, eggs with flax eggs or aquafaba
- **Gluten-free**: Substitute wheat flour 1:1 with GF blend; note that xanthan gum may be needed for baking
- **Low-carb/keto**: Replace starchy ingredients (flour, sugar, potatoes) with cauliflower, almond flour, erythritol
- **Dairy-free**: Swap dairy milk/cream with oat/almond/soy milk; butter with coconut oil

## Meal Planning

When helping with weekly meal planning:
1. Ask about dietary preferences, restrictions, and servings needed
2. Balance nutrition across the week (protein, vegetables, carbs)
3. Suggest batch cooking opportunities (cook once, eat twice)
4. Generate a consolidated shopping list from all planned recipes

## Shopping List from Recipe

When generating shopping lists from recipes:
- Group ingredients by store section (produce, dairy, meat, pantry, etc.)
- Consolidate duplicates (e.g., "2 onions" from recipe A + "1 onion" from recipe B = "3 onions")
- Exclude items the user likely has (salt, pepper, common spices)—unless they ask to include them
- Note brand or variety preferences if specified in the recipe

## Cooking Technique Tips

See `references/cooking-techniques.md` for guidance on:
- Knife skills and prep techniques
- Common cooking methods (sauté, braise, roast, poach)
- Baking fundamentals (leavening, hydration, gluten development)
- Temperature guides for meat doneness
