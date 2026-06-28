"""Load and use exported face encodings from encoded_result folder.

This demonstrates how to load the encodings exported by export_encodings.py
and use them for face matching without re-encoding.

Usage:
    python load_encodings.py <query_image.png> [--encoded-dir ENCODED_DIR]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from facial_recognition.encoder import Encoder
from facial_recognition.matcher import Matcher
from facial_recognition.models import GalleryEncodingSet

DEFAULT_ENCODED_DIR = r"d:\Mini-Project\FM\encoded_result"


def load_encodings_from_export(encoded_dir: str) -> GalleryEncodingSet:
    """Load all encodings from the encoded_result folder.
    
    Args:
        encoded_dir: Directory containing manifest.json and .npy files
        
    Returns:
        GalleryEncodingSet ready for matching
    """
    manifest_path = os.path.join(encoded_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(
            f"Manifest file not found: {manifest_path}\n"
            "Run export_encodings.py first to generate encodings."
        )
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    if not manifest:
        raise ValueError("Manifest is empty - no encodings available")
    
    # Load all encodings
    filenames = []
    encodings = []
    
    for entry in manifest.values():
        encoding_file = os.path.join(encoded_dir, entry['encoding_file'])
        encoding = np.load(encoding_file)
        
        filenames.append(entry['basename'])
        encodings.append(encoding)
    
    # Stack into matrix
    matrix = np.stack(encodings)
    
    return GalleryEncodingSet(filenames=filenames, matrix=matrix)


def main():
    parser = argparse.ArgumentParser(
        description="Match a query face against exported encodings"
    )
    parser.add_argument(
        'query',
        help="Path to query image"
    )
    parser.add_argument(
        '--encoded-dir',
        default=DEFAULT_ENCODED_DIR,
        help=f"Directory with exported encodings (default: {DEFAULT_ENCODED_DIR})"
    )
    parser.add_argument(
        '--model',
        choices=['hog', 'cnn'],
        default='hog',
        help="Face detection model for query image"
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.6,
        help="Distance threshold for same-person match (default: 0.6)"
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help="Number of top matches to show (default: 5)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.isfile(args.query):
        print(f"Error: Query image not found: {args.query}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.encoded_dir):
        print(f"Error: Encoded directory not found: {args.encoded_dir}", file=sys.stderr)
        print("Run export_encodings.py first to generate encodings.", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load pre-computed gallery encodings
        print(f"Loading encodings from {args.encoded_dir}...")
        gallery = load_encodings_from_export(args.encoded_dir)
        print(f"Loaded {len(gallery)} face encodings\n")
        
        # Encode query image
        print(f"Encoding query image: {args.query}")
        encoder = Encoder(model=args.model)
        query_encoding = encoder.encode_image(args.query)
        
        if query_encoding is None:
            print("Error: No face detected in query image", file=sys.stderr)
            sys.exit(2)
        
        print("Query encoded successfully\n")
        
        # Match against gallery
        matcher = Matcher(threshold=args.threshold)
        results = matcher.rank(query_encoding, gallery, top_k=args.top_k)
        
        if not results:
            print("No matches found (gallery is empty or top-k is 0)")
            sys.exit(0)
        
        # Display results
        print("="*70)
        print("MATCH RESULTS")
        print("="*70)
        
        for i, result in enumerate(results, 1):
            same_person = "✓ SAME PERSON" if result.is_match else "  different"
            print(f"\n#{i}  {result.filename}")
            print(f"     Similarity: {result.similarity:.4f}")
            print(f"     Distance:   {result.distance:.4f}")
            print(f"     {same_person}")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
