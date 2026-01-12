#!/usr/bin/env python3
"""
Unified seed script for importing all vocabulary words with image compression.

This script:
1. Reads words_seed/words_all.json (7,524 words)
2. Compresses images from words_seed/vocab_all/ to WebP format
3. Imports words to database with appropriate image URLs

Usage:
    # Local mode: image_url = /static/images/xxx.webp
    python scripts/seed_all_words.py --local

    # Remote mode: image_url = https://storage.googleapis.com/coach-vocab-static/images/xxx.webp
    python scripts/seed_all_words.py --remote

    # Skip compression (use existing images)
    python scripts/seed_all_words.py --local --skip-compress

    # Custom database URL
    DATABASE_URL="postgresql://..." python scripts/seed_all_words.py --remote --skip-compress
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
WORDS_SEED_DIR = PROJECT_ROOT / "words_seed"
WORDS_JSON = WORDS_SEED_DIR / "words_all.json"
VOCAB_ALL_DIR = WORDS_SEED_DIR / "vocab_all"
STATIC_IMAGES_DIR = PROJECT_ROOT / "static" / "images"

# GCS configuration
GCS_BUCKET = "coach-vocab-static"
GCS_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/images"


def get_local_image_url(filename: str) -> str:
    """Generate local static file URL."""
    return f"/static/images/{filename}"


def get_remote_image_url(filename: str) -> str:
    """Generate GCS public URL."""
    return f"{GCS_BASE_URL}/{filename}"


def compress_images(source_dir: Path, output_dir: Path, workers: int = 4) -> dict:
    """
    Compress all images from source directory.

    Returns mapping of original filename to new filename.
    """
    # Import compress module
    from compress_images import compress_images_batch

    return compress_images_batch(
        str(source_dir),
        str(output_dir),
        max_size=800,
        quality=80,
        use_hash_names=True,
        workers=workers
    )


def load_words() -> list:
    """Load words from JSON file."""
    if not WORDS_JSON.exists():
        print(f"Error: Words file not found: {WORDS_JSON}")
        sys.exit(1)

    with open(WORDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def build_words_data(
    raw_words: list,
    image_mapping: dict,
    url_generator: callable
) -> list:
    """
    Build word data list with image URLs.

    Args:
        raw_words: List of raw word dictionaries
        image_mapping: Dict mapping original filename to new filename
        url_generator: Function to generate image URL from filename
    """
    words_data = []
    missing_images = 0

    for raw_word in raw_words:
        image_file = raw_word.get("image_file")
        image_url = None

        if image_file and image_file in image_mapping:
            new_filename = image_mapping[image_file]
            image_url = url_generator(new_filename)
        elif image_file:
            missing_images += 1
            if missing_images <= 5:
                print(f"Warning: No compressed image for '{raw_word['word']}' ({image_file})")

        word_data = {
            "word": raw_word["word"],
            "translation": raw_word["translation"],
            "sentence": None,
            "sentence_zh": None,
            "image_url": image_url,
            "audio_url": raw_word.get("audio_url"),
            "level_id": raw_word.get("level_id"),
            "category_id": raw_word.get("category_id"),
        }
        words_data.append(word_data)

    if missing_images > 5:
        print(f"... and {missing_images - 5} more missing images")

    return words_data


def import_to_database(words_data: list, batch_size: int = 500):
    """Import words to database."""
    sys.path.insert(0, str(PROJECT_ROOT))

    from app.database import SessionLocal
    from app.models.word import Word

    db = SessionLocal()
    try:
        # Clear existing words
        deleted = db.query(Word).delete()
        db.commit()
        print(f"Cleared {deleted} existing words")

        # Batch insert
        total = len(words_data)
        imported = 0

        for i in range(0, total, batch_size):
            batch = words_data[i:i + batch_size]
            word_objects = [Word(**data) for data in batch]
            db.bulk_save_objects(word_objects)
            db.commit()

            imported += len(batch)
            if imported % 1000 == 0 or imported == total:
                pct = (imported / total) * 100
                print(f"Imported: {imported}/{total} ({pct:.1f}%)")

        print(f"\nSuccessfully imported {imported} words")
        return imported

    except Exception as e:
        db.rollback()
        print(f"Error importing to database: {e}")
        raise
    finally:
        db.close()


def load_existing_mapping(output_dir: Path) -> dict:
    """
    Load image mapping from existing compressed images.

    Scans the output directory and builds a mapping based on
    finding corresponding source files.
    """
    if not output_dir.exists():
        return {}

    # Get all webp files in output directory
    webp_files = list(output_dir.glob("*.webp"))
    if not webp_files:
        return {}

    print(f"Found {len(webp_files)} existing compressed images")

    # We need to rebuild the mapping by checking which source files
    # produce which hash. This is computationally expensive, so we'll
    # look for a cached mapping file first.
    mapping_file = output_dir / ".image_mapping.json"
    if mapping_file.exists():
        with open(mapping_file, "r") as f:
            mapping = json.load(f)
            print(f"Loaded cached mapping with {len(mapping)} entries")
            return mapping

    print("No cached mapping found. Building from scratch...")
    print("(This may take a while for 7500+ images)")

    # Import hash function
    from compress_images import get_file_hash

    mapping = {}
    source_files = list(VOCAB_ALL_DIR.glob("*.png"))

    for i, source_file in enumerate(source_files):
        file_hash = get_file_hash(str(source_file))
        expected_webp = f"{file_hash}.webp"
        webp_path = output_dir / expected_webp

        if webp_path.exists():
            mapping[source_file.name] = expected_webp

        if (i + 1) % 1000 == 0:
            print(f"Scanned: {i + 1}/{len(source_files)}")

    # Cache the mapping
    with open(mapping_file, "w") as f:
        json.dump(mapping, f)
    print(f"Built and cached mapping with {len(mapping)} entries")

    return mapping


def main():
    parser = argparse.ArgumentParser(
        description="Seed all vocabulary words with image compression"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Local mode: use /static/images/ URLs"
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Remote mode: use GCS URLs"
    )
    parser.add_argument(
        "--skip-compress",
        action="store_true",
        help="Skip image compression (use existing images)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for compression (default: 4)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Database batch size (default: 500)"
    )

    args = parser.parse_args()

    # Validate mode
    if not args.local and not args.remote:
        print("Error: Must specify --local or --remote mode")
        parser.print_help()
        sys.exit(1)

    if args.local and args.remote:
        print("Error: Cannot specify both --local and --remote")
        sys.exit(1)

    # Determine URL generator
    if args.local:
        url_generator = get_local_image_url
        mode_name = "LOCAL"
    else:
        url_generator = get_remote_image_url
        mode_name = "REMOTE"

    print("=" * 60)
    print(f"Vocabulary Seed Script - {mode_name} MODE")
    print("=" * 60)
    print(f"Words source: {WORDS_JSON}")
    print(f"Images source: {VOCAB_ALL_DIR}")
    print(f"Images output: {STATIC_IMAGES_DIR}")
    print(f"Skip compression: {args.skip_compress}")
    print("=" * 60)

    # Load words
    print("\n[1/4] Loading words...")
    raw_words = load_words()
    print(f"Loaded {len(raw_words)} words")

    # Compress images or load existing mapping
    print("\n[2/4] Processing images...")
    if args.skip_compress:
        image_mapping = load_existing_mapping(STATIC_IMAGES_DIR)
        if not image_mapping:
            print("Warning: No existing images found. Run without --skip-compress first.")
    else:
        # Ensure output directory exists
        STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        image_mapping = compress_images(
            VOCAB_ALL_DIR,
            STATIC_IMAGES_DIR,
            workers=args.workers
        )

        # Cache the mapping for future use
        mapping_file = STATIC_IMAGES_DIR / ".image_mapping.json"
        with open(mapping_file, "w") as f:
            json.dump(image_mapping, f)
        print(f"Cached mapping to {mapping_file}")

    print(f"Image mapping has {len(image_mapping)} entries")

    # Build word data
    print("\n[3/4] Building word data...")
    words_data = build_words_data(raw_words, image_mapping, url_generator)
    words_with_images = sum(1 for w in words_data if w["image_url"])
    print(f"Words with images: {words_with_images}/{len(words_data)}")

    # Import to database
    print("\n[4/4] Importing to database...")
    import_to_database(words_data, batch_size=args.batch_size)

    print("\n" + "=" * 60)
    print("SEED COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
