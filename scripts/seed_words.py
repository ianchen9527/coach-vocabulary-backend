#!/usr/bin/env python3
"""
Seed script to import words from words.json and process images.

This script:
1. Reads words.json
2. Calculates hash for each image and renames it
3. Copies images to static/images/
4. Imports words to database via API or directly

Usage:
    python scripts/seed_words.py [--direct]

Options:
    --direct    Import directly to database (requires DB connection)
                Without this flag, outputs JSON for API import
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
WORDS_JSON = PROJECT_ROOT / "words.json"
VOCAB_DIR = PROJECT_ROOT / "vocab"
STATIC_IMAGES_DIR = PROJECT_ROOT / "static" / "images"


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file and return first 12 characters."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()[:12]


def process_words():
    """Process words.json and images."""
    # Load words.json
    with open(WORDS_JSON, "r", encoding="utf-8") as f:
        raw_words = json.load(f)

    # Ensure static/images directory exists
    STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    processed_words = []
    image_mapping = {}  # word -> new filename

    for raw_word in raw_words:
        word = raw_word["word"]

        # Find image file
        image_source = VOCAB_DIR / raw_word.get("image_file")
        image_url = None

        if image_source.exists():
            # Calculate hash
            file_hash = calculate_file_hash(image_source)
            new_filename = f"{file_hash}.png"
            image_dest = STATIC_IMAGES_DIR / new_filename

            # Copy if not exists (avoid duplicate copies)
            if not image_dest.exists():
                shutil.copy2(image_source, image_dest)
                print(f"Copied: {word}.png -> {new_filename}")
            else:
                print(f"Exists: {new_filename} (from {word}.png)")

            image_url = f"/static/images/{new_filename}"
            image_mapping[word] = new_filename
        else:
            print(f"Warning: No image found for '{word}'")

        # Build cleaned word data (remove redundant fields)
        processed_word = {
            "word": word,
            "translation": raw_word["translation"],
            "sentence": raw_word.get("sentence"),
            "sentence_zh": raw_word.get("sentence_zh"),
            "image_url": image_url,
            "audio_url": None,  # Audio files not available yet
            "level_id": raw_word.get("level_id"),
            "category_id": raw_word.get("category_id"),
        }
        processed_words.append(processed_word)

    return processed_words, image_mapping


def direct_import(words_data):
    """Import words directly to database."""
    # Add project root to path for imports
    sys.path.insert(0, str(PROJECT_ROOT))

    from app.database import SessionLocal
    from app.repositories.word_repository import WordRepository

    db = SessionLocal()
    try:
        word_repo = WordRepository(db)

        # Clear existing words
        word_repo.delete_all()
        print("Cleared existing words")

        # Bulk create
        imported, skipped = word_repo.bulk_create(words_data)
        print(f"Imported: {imported}, Skipped: {skipped}")

        return imported, skipped
    finally:
        db.close()


def output_json(words_data):
    """Output JSON for API import."""
    output = {
        "words": words_data,
        "clear_existing": True,
    }

    output_file = PROJECT_ROOT / "data" / "seed_words.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput saved to: {output_file}")
    print(f"Total words: {len(words_data)}")
    print("\nTo import via API:")
    print(f'  curl -X POST http://localhost:8000/api/admin/seed-words \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d @data/seed_words.json')


def main():
    direct_mode = "--direct" in sys.argv

    print("Processing words and images...")
    print(f"Source: {WORDS_JSON}")
    print(f"Images: {VOCAB_DIR}")
    print(f"Output: {STATIC_IMAGES_DIR}")
    print("-" * 50)

    words_data, image_mapping = process_words()

    print("-" * 50)
    print(f"Processed {len(words_data)} words")
    print(f"Images copied: {len(image_mapping)}")

    if direct_mode:
        print("\nImporting directly to database...")
        direct_import(words_data)
    else:
        output_json(words_data)


if __name__ == "__main__":
    main()
