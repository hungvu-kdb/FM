"""Export face encodings to a parseable format in encoded_result folder.

This script encodes all face images in the sample gallery and saves them to
d:\Mini-Project\FM\encoded_result\ as individual .npy files keyed by the
original file path (with a sanitized filename).

Usage:
    python export_encodings.py [--gallery GALLERY_DIR] [--output OUTPUT_DIR] [--model hog|cnn]

The output structure:
    encoded_result/
        ├── manifest.json          # Maps original paths to encoding files
        ├── 1.npy                  # Encoding for 1.png
        ├── 100007.npy             # Encoding for 100007.png
        └── ...
"""

import argparse
import json
import os
import sys

# Add the parent directory to path so we can import facial_recognition
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from facial_recognition.encoder import Encoder, ImageDecodeError

DEFAULT_GALLERY = r"d:\Mini-Project\FM\sample"
DEFAULT_OUTPUT = r"d:\Mini-Project\FM\encoded_result"


def sanitize_filename(basename: str) -> str:
    """Convert image basename to encoding output filename.
    
    Example: "100007.png" -> "100007.npy"
    """
    name_without_ext = os.path.splitext(basename)[0]
    return f"{name_without_ext}.npy"


def export_encodings(gallery_dir: str, output_dir: str, model: str = "hog") -> None:
    """Export all face encodings from gallery_dir to output_dir.
    
    Args:
        gallery_dir: Directory containing PNG face images
        output_dir: Directory to save .npy encodings and manifest.json
        model: Face detection model ("hog" or "cnn")
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all PNG files
    png_files = sorted(
        f for f in os.listdir(gallery_dir)
        if f.lower().endswith('.png') and os.path.isfile(os.path.join(gallery_dir, f))
    )
    
    if not png_files:
        print(f"No PNG files found in {gallery_dir}")
        return
    
    print(f"Found {len(png_files)} PNG files in gallery")
    print(f"Using {model} detector model")
    print(f"Output directory: {output_dir}\n")
    
    encoder = Encoder(model=model)
    manifest = {}
    successful = 0
    skipped = 0
    
    for filename in png_files:
        image_path = os.path.join(gallery_dir, filename)
        output_filename = sanitize_filename(filename)
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            # Encode the face
            encoding = encoder.encode_image(image_path)
            
            if encoding is None:
                print(f"⚠️  SKIP: {filename} (no face detected)")
                skipped += 1
                continue
            
            # Save encoding as .npy file
            np.save(output_path, encoding)
            
            # Record in manifest
            manifest[image_path] = {
                "original_path": image_path,
                "basename": filename,
                "encoding_file": output_filename,
                "encoding_shape": list(encoding.shape),
                "encoding_dtype": str(encoding.dtype)
            }
            
            print(f"✓ {filename} -> {output_filename}")
            successful += 1
            
        except ImageDecodeError as e:
            print(f"⚠️  SKIP: {filename} (decode error: {e})")
            skipped += 1
        except Exception as e:
            print(f"❌ ERROR: {filename} ({e})")
            skipped += 1
    
    # Save manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Export complete!")
    print(f"  ✓ Successful: {successful}")
    print(f"  ⚠️  Skipped: {skipped}")
    print(f"  📁 Output: {output_dir}")
    print(f"  📄 Manifest: {manifest_path}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Export face encodings from gallery to encoded_result folder"
    )
    parser.add_argument(
        '--gallery',
        default=DEFAULT_GALLERY,
        help=f"Gallery directory (default: {DEFAULT_GALLERY})"
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        '--model',
        choices=['hog', 'cnn'],
        default='hog',
        help="Face detection model: 'hog' (fast, CPU) or 'cnn' (accurate, slower)"
    )
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.gallery):
        print(f"Error: Gallery directory does not exist: {args.gallery}", file=sys.stderr)
        sys.exit(1)
    
    try:
        export_encodings(args.gallery, args.output, args.model)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
