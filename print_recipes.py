import json
with open('missing_recipes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    for d in data[:10]:
        print("ID:", d['id'])
        print("Titol:", d['titol'])
        print("Ingredients:", d['ingredients'])
        print("Instruccions:", str(d['instruccions'])[:100] + '...')
        print("-" * 40)
