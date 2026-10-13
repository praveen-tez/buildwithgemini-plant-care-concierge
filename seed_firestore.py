#!/usr/bin/env python3
import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-839801f0229c"

db = firestore.Client(project=PROJECT_ID)

plants = [
    {
        "id": "monstera-deliciosa",
        "name": "Monstera Deliciosa",
        "species": "Monstera deliciosa",
        "light_level": "Bright indirect",
        "watering_frequency_days": 7,
        "difficulty": "Easy",
        "description": "Popular tropical plant with iconic split leaves (fenestrations). Thrives in warm, humid rooms.",
        "last_watered": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat(),
        "notes": "Keep soil lightly moist; wipe down leaves occasionally."
    },
    {
        "id": "snake-plant",
        "name": "Snake Plant (Sansevieria)",
        "species": "Dracaena trifasciata",
        "light_level": "Low to bright indirect",
        "watering_frequency_days": 14,
        "difficulty": "Very Easy",
        "description": "Extremely hardy plant with upright, sword-like green foliage with yellow margins. Tolerates neglect.",
        "last_watered": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10)).isoformat(),
        "notes": "Let soil completely dry out between waterings."
    },
    {
        "id": "fiddle-leaf-fig",
        "name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "light_level": "Bright indirect",
        "watering_frequency_days": 7,
        "difficulty": "Medium",
        "description": "Dramatic indoor tree with large, violin-shaped leathery leaves.",
        "last_watered": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=6)).isoformat(),
        "notes": "Sensitive to drafts and temperature shifts. Needs steady light."
    },
    {
        "id": "pothos-golden",
        "name": "Golden Pothos",
        "species": "Epipremnum aureum",
        "light_level": "Low to medium indirect",
        "watering_frequency_days": 7,
        "difficulty": "Easy",
        "description": "Fast-growing trailing vine with heart-shaped leaves variegated with gold.",
        "last_watered": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).isoformat(),
        "notes": "Great for hanging baskets or cascading off shelves."
    }
]

def seed():
    print(f"Seeding plants collection into project: {PROJECT_ID}...")
    batch = db.batch()
    col = db.collection("plants")
    for plant in plants:
        doc_ref = col.document(plant["id"])
        batch.set(doc_ref, plant)
    batch.commit()
    print(f"Successfully seeded {len(plants)} plants into Firestore!")

if __name__ == "__main__":
    seed()
