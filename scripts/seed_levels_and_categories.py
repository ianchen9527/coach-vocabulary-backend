#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import SessionLocal
from app.models.word_level import WordLevel
from app.models.word_category import WordCategory

def seed_levels(db):
    levels_data = [
        (1, "A1.1"),
        (2, "A1.2"),
        (3, "A2.1"),
        (4, "A2.2"),
        (5, "B1.1"),
        (6, "B1.2"),
        (7, "B2.1"),
        (8, "B2.2"),
    ]

    print("Seeding levels...")
    for order, label in levels_data:
        existing_level = db.query(WordLevel).filter_by(id=order).first()
        if existing_level:
            print(f"  Skipping: Level {order} ({label}) already exists.")
            continue
            
        level = WordLevel(id=order, label=label, order=order)
        db.add(level)
    
    db.commit()
    print("  Levels seeding completed.")

def seed_categories(db):
    categories_data = [
        (1, "Function Words"),
        (2, "Basic Descriptors"),
        (3, "Time & Space"),
        (4, "Family & Relationships"),
        (5, "Body & Health"),
        (6, "Food & Drink"),
        (7, "Home & Daily Routine"),
        (8, "Clothing & Fashion"),
        (9, "Feelings & Emotions"),
        (10, "Transport & Travel"),
        (11, "Communication & Media"),
        (12, "Education"),
        (13, "Jobs & Work"),
        (14, "Sports & Games"),
        (15, "Nature & Animals"),
        (16, "Business & Money"),
        (17, "Arts & Entertainment"),
        (18, "Science & Technology"),
        (19, "Society & Culture"),
        (20, "Law & Politics"),
    ]

    print("Seeding categories...")
    for order, label in categories_data:
        existing_category = db.query(WordCategory).filter_by(id=order).first()
        if existing_category:
            print(f"  Skipping: Category {order} ({label}) already exists.")
            continue

        category = WordCategory(id=order, label=label, order=order)
        db.add(category)
    
    db.commit()
    print("  Categories seeding completed.")

def main():
    db = SessionLocal()
    try:
        seed_levels(db)
        seed_categories(db)
    finally:
        db.close()

if __name__ == "__main__":
    main()
