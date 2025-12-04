from app.core.db import get_db
db = get_db()
cities = list(db.cities.find({"is_active": True}, {"_id": 1, "name": 1}).sort("_id", 1))
print(f"Total active cities: {len(cities)}")
for c in cities:
    print(f"{c['_id']} {c['name']}")
