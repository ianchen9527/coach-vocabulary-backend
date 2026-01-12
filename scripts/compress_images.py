#!/usr/bin/env python3
"""
Image compression utility for vocabulary images.

Compresses PNG images to WebP format with configurable quality and size.
Uses content-based hashing for filenames to enable deduplication.
"""

import hashlib
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image


def get_file_hash(file_path: str, length: int = 12) -> str:
    """Calculate SHA256 hash of file content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()[:length]


def compress_image(
    input_path: str,
    output_path: str,
    max_size: int = 800,
    quality: int = 80
) -> tuple[str, int, int]:
    """
    Compress an image to WebP format.

    Args:
        input_path: Path to source image
        output_path: Path for compressed output
        max_size: Maximum dimension (width or height)
        quality: WebP quality (0-100)

    Returns:
        Tuple of (output_path, original_size, compressed_size)
    """
    original_size = os.path.getsize(input_path)

    with Image.open(input_path) as img:
        # Convert to RGB if necessary (remove alpha channel)
        if img.mode in ('RGBA', 'P', 'LA'):
            # Create white background for transparent images
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize if larger than max_size (maintain aspect ratio)
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Save as WebP
        img.save(output_path, 'WEBP', quality=quality, method=6)

    compressed_size = os.path.getsize(output_path)
    return output_path, original_size, compressed_size


def compress_images_batch(
    input_dir: str,
    output_dir: str,
    max_size: int = 800,
    quality: int = 80,
    use_hash_names: bool = True,
    workers: int = 4
) -> dict[str, str]:
    """
    Compress all images in a directory.

    Args:
        input_dir: Source directory containing images
        output_dir: Destination directory for compressed images
        max_size: Maximum dimension for images
        quality: WebP quality (0-100)
        use_hash_names: If True, use content hash as filename
        workers: Number of parallel workers

    Returns:
        Dictionary mapping original filename to new filename
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all image files
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    image_files = [
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    total_files = len(image_files)
    if total_files == 0:
        print("No images found in input directory.")
        return {}

    print(f"Found {total_files} images to compress...")
    print(f"Settings: max_size={max_size}, quality={quality}")
    print("-" * 50)

    mapping = {}
    total_original = 0
    total_compressed = 0
    processed = 0

    def process_image(img_file: Path) -> tuple[str, str, int, int]:
        """Process a single image."""
        if use_hash_names:
            file_hash = get_file_hash(str(img_file))
            new_filename = f"{file_hash}.webp"
        else:
            new_filename = f"{img_file.stem}.webp"

        output_file = output_path / new_filename
        _, orig_size, comp_size = compress_image(
            str(img_file), str(output_file), max_size, quality
        )
        return img_file.name, new_filename, orig_size, comp_size

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_image, img_file): img_file
            for img_file in image_files
        }

        for future in as_completed(futures):
            try:
                orig_name, new_name, orig_size, comp_size = future.result()
                mapping[orig_name] = new_name
                total_original += orig_size
                total_compressed += comp_size
                processed += 1

                if processed % 100 == 0 or processed == total_files:
                    pct = (processed / total_files) * 100
                    print(f"Progress: {processed}/{total_files} ({pct:.1f}%)")

            except Exception as e:
                img_file = futures[future]
                print(f"Error processing {img_file}: {e}", file=sys.stderr)

    # Print summary
    print("-" * 50)
    print(f"Compression complete!")
    print(f"  Files processed: {processed}/{total_files}")
    print(f"  Original size: {total_original / (1024*1024):.1f} MB")
    print(f"  Compressed size: {total_compressed / (1024*1024):.1f} MB")
    if total_original > 0:
        ratio = (1 - total_compressed / total_original) * 100
        print(f"  Space saved: {ratio:.1f}%")

    return mapping


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compress images to WebP format")
    parser.add_argument("input_dir", help="Input directory containing images")
    parser.add_argument("output_dir", help="Output directory for compressed images")
    parser.add_argument("--max-size", type=int, default=800,
                        help="Maximum dimension (default: 800)")
    parser.add_argument("--quality", type=int, default=80,
                        help="WebP quality 0-100 (default: 80)")
    parser.add_argument("--no-hash", action="store_true",
                        help="Don't use hash-based filenames")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers (default: 4)")
    parser.add_argument("--mapping-file", type=str,
                        help="Output file for filename mapping (JSON)")

    args = parser.parse_args()

    mapping = compress_images_batch(
        args.input_dir,
        args.output_dir,
        max_size=args.max_size,
        quality=args.quality,
        use_hash_names=not args.no_hash,
        workers=args.workers
    )

    if args.mapping_file:
        import json
        with open(args.mapping_file, 'w') as f:
            json.dump(mapping, f, indent=2)
        print(f"Mapping saved to: {args.mapping_file}")
