"""Pre-encode all gallery images and save embeddings to disk.

This script encodes all images in a gallery directory and saves the embeddings
to a numpy file for fast loading. This is useful for:
- Large galleries (100+ images)
- Avoiding repeated encoding
- Faster app startup time
"""

import os
import argparse
import time
from typing import Dict, List
import numpy as np
from tqdm import tqdm

from CNN import CNNEncoder, CNNCache, CNNCacheEntry, ImageDecodeError


def list_png_files(directory: str) -> List[str]:
    """List all PNG files in directory."""
    files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.png'):
            files.append(os.path.join(directory, filename))
    return sorted(files)


def encode_gallery_with_progress(
    encoder: CNNEncoder,
    gallery_dir: str,
    cache_path: str,
    force_reencode: bool = False
) -> Dict[str, CNNCacheEntry]:
    """Encode all gallery images with progress bar.
    
    Args:
        encoder: CNNEncoder instance.
        gallery_dir: Directory containing gallery images.
        cache_path: Path to save cache file.
        force_reencode: If True, re-encode all images even if cached.
        
    Returns:
        Dictionary of image_path -> CNNCacheEntry.
    """
    cache = CNNCache(cache_path)
    
    # Load existing cache
    if not force_reencode:
        print("Loading existing cache...")
        cached_entries = cache.load()
        print(f"Found {len(cached_entries)} cached entries")
    else:
        print("Force re-encode enabled, ignoring cache")
        cached_entries = {}
    
    # Get all PNG files
    image_paths = list_png_files(gallery_dir)
    print(f"\nFound {len(image_paths)} PNG files in gallery")
    
    if not image_paths:
        print("No PNG files found!")
        return {}
    
    entries: Dict[str, CNNCacheEntry] = {}
    stats = {
        'reused': 0,
        'encoded': 0,
        'failed': 0,
        'no_face': 0
    }
    
    # Process each image with progress bar
    print("\nProcessing images...")
    for image_path in tqdm(image_paths, desc="Encoding", unit="img"):
        filename = os.path.basename(image_path)
        
        # Get file signature
        size, mtime = cache.file_signature(image_path)
        sig = (size, mtime)
        
        # Check if we can reuse cached entry
        if not force_reencode and image_path in cached_entries:
            if cached_entries[image_path].signature == sig:
                # Reuse cached entry
                entries[image_path] = cached_entries[image_path]
                stats['reused'] += 1
                continue
        
        # Encode the image
        try:
            embedding = encoder.encode_image(image_path)
            
            if embedding is not None:
                entries[image_path] = CNNCacheEntry(
                    image_path=image_path,
                    size_bytes=size,
                    mtime=mtime,
                    embedding=embedding
                )
                stats['encoded'] += 1
            else:
                stats['no_face'] += 1
                tqdm.write(f"  ⚠️  No face detected: {filename}")
                
        except ImageDecodeError as e:
            stats['failed'] += 1
            tqdm.write(f"  ❌ Failed to decode: {filename}")
        except Exception as e:
            stats['failed'] += 1
            tqdm.write(f"  ❌ Error processing {filename}: {e}")
    
    # Save cache
    print("\nSaving cache to disk...")
    cache.save(entries)
    
    # Print statistics
    print("\n" + "="*60)
    print("Encoding Statistics:")
    print("="*60)
    print(f"Total images:        {len(image_paths)}")
    print(f"Successfully encoded: {len(entries)}")
    print(f"  - Reused from cache: {stats['reused']}")
    print(f"  - Newly encoded:     {stats['encoded']}")
    print(f"No face detected:    {stats['no_face']}")
    print(f"Failed to process:   {stats['failed']}")
    print("="*60)
    
    if len(entries) > 0:
        print(f"\n✅ Cache saved to: {cache_path}")
        print(f"📊 Total valid entries: {len(entries)}")
    else:
        print("\n⚠️  No valid entries to save!")
    
    return entries


def verify_cache(cache_path: str) -> None:
    """Verify that cache can be loaded and display info."""
    print("\n" + "="*60)
    print("Verifying Cache File")
    print("="*60)
    
    if not os.path.exists(cache_path):
        print(f"❌ Cache file not found: {cache_path}")
        return
    
    cache = CNNCache(cache_path)
    entries = cache.load()
    
    if not entries:
        print("❌ Cache is empty or corrupted")
        return
    
    print(f"✅ Cache loaded successfully")
    print(f"📊 Total entries: {len(entries)}")
    
    # Calculate cache size
    file_size = os.path.getsize(cache_path)
    size_mb = file_size / (1024 * 1024)
    print(f"💾 Cache file size: {size_mb:.2f} MB")
    
    # Show sample entries
    print("\n📝 Sample entries:")
    for i, (path, entry) in enumerate(list(entries.items())[:5]):
        filename = os.path.basename(path)
        print(f"  {i+1}. {filename}")
        print(f"     Size: {entry.size_bytes} bytes, mtime: {entry.mtime}")
        print(f"     Embedding shape: {entry.embedding.shape}")
    
    if len(entries) > 5:
        print(f"  ... and {len(entries) - 5} more")
    
    print("="*60)


def export_embeddings_separately(
    cache_path: str,
    output_dir: str
) -> None:
    """Export individual embedding files for each image.
    
    Args:
        cache_path: Path to cache file.
        output_dir: Directory to save individual embedding files.
    """
    print("\n" + "="*60)
    print("Exporting Individual Embeddings")
    print("="*60)
    
    cache = CNNCache(cache_path)
    entries = cache.load()
    
    if not entries:
        print("❌ No entries to export")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Exporting {len(entries)} embeddings to: {output_dir}")
    
    for image_path, entry in tqdm(entries.items(), desc="Exporting", unit="file"):
        filename = os.path.basename(image_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # Save as .npy file
        npy_path = os.path.join(output_dir, f"{name_without_ext}.npy")
        np.save(npy_path, entry.embedding)
    
    print(f"\n✅ Exported {len(entries)} embedding files")
    print(f"📁 Location: {output_dir}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-encode gallery images and save embeddings"
    )
    parser.add_argument(
        "gallery_dir",
        nargs="?",
        default=r"d:\Mini-Project\FM\sample",
        help="Directory containing gallery images (default: sample)"
    )
    parser.add_argument(
        "--cache-name",
        default=".cnn_encodings.npz",
        help="Cache filename (default: .cnn_encodings.npz)"
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu", "auto"],
        default="auto",
        help="Device to use for encoding (default: auto)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-encode all images, ignoring cache"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify cache after encoding"
    )
    parser.add_argument(
        "--export",
        metavar="DIR",
        help="Export individual .npy files to specified directory"
    )
    
    args = parser.parse_args()
    
    # Validate gallery directory
    if not os.path.isdir(args.gallery_dir):
        print(f"❌ Gallery directory not found: {args.gallery_dir}")
        return 1
    
    cache_path = os.path.join(args.gallery_dir, args.cache_name)
    
    print("="*60)
    print("  Gallery Pre-Encoding Tool")
    print("="*60)
    print(f"Gallery directory: {args.gallery_dir}")
    print(f"Cache file:        {cache_path}")
    print(f"Device:            {args.device}")
    print(f"Force re-encode:   {args.force}")
    print("="*60)
    
    # Initialize encoder
    print("\nInitializing CNN encoder...")
    device = None if args.device == "auto" else args.device
    start_time = time.time()
    
    try:
        encoder = CNNEncoder(device=device)
        print("✅ Encoder initialized")
        
        # Encode gallery
        entries = encode_gallery_with_progress(
            encoder,
            args.gallery_dir,
            cache_path,
            force_reencode=args.force
        )
        
        elapsed = time.time() - start_time
        print(f"\n⏱️  Total time: {elapsed:.2f} seconds")
        
        if entries:
            avg_time = elapsed / len(entries)
            print(f"⏱️  Average time per image: {avg_time:.3f} seconds")
        
        # Verify cache if requested
        if args.verify:
            verify_cache(cache_path)
        
        # Export individual files if requested
        if args.export:
            export_embeddings_separately(cache_path, args.export)
        
        print("\n✅ Done!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    
    # Check if tqdm is available
    try:
        import tqdm
    except ImportError:
        print("⚠️  Installing tqdm for progress bars...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        print("✅ tqdm installed, please run the script again")
        sys.exit(0)
    
    sys.exit(main())
