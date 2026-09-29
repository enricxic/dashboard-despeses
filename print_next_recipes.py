import json
with open('missing_recipes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    for d in data[10:20]:
        print(f"ID: {d['id']} | Títol: {d['titol']}")
        print(f"Ingredients: {d.get('ingredients', '')}")
        print("-" * 40)
