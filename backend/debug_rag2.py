import json
for r in json.load(open("recipes.json")):
    if r["title"] == "Chicken Mandi":
        print(r["ingredients"])
