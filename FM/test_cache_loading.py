"""Test script to debug cache loading issue."""

import os
import json
import numpy as np
from CNN import CNNGallerySet, EMBEDDING_DIM

ENCODED_RESULT_DIR = r"d:\Mini-Project\FM\encoded_result"

def test_load_encodings():
    """Test loading encodings from encoded_result directory."""
    manifest_path = os.path.join(ENCODED_RESULT_DIR, "manifest.json")
    
    print(f"Checking manifest path: {manifest_path}")
    print(f"Manifest exists: {os.path.exists(manifest_path)}")
    
    if not os.path.exists(manifest_path):
        print("❌ Manifest file not found!")
        return None
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print(f"✅ Loaded manifest with {len(manifest)} entries")
        
        if not manifest:
            print("❌ Manifest is empty")
            return None
        
        # Show first entry
        first_key = list(manifest.keys())[0]
        print(f"\nFirst entry: {first_key}")
        print(f"Details: {manifest[first_key]}")
        
        # Load all encodings
        filenames = []
        embeddings = []
        
        missing_files = []
        for idx, entry in enumerate(manifest.values()):
            encoding_file = os.path.join(ENCODED_RESULT_DIR, entry['encoding_file'])
            
            if idx < 3:  # Show first 3
                print(f"\nChecking file {idx+1}: {entry['encoding_file']}")
                print(f"  Full path: {encoding_file}")
                print(f"  Exists: {os.path.exists(encoding_file)}")
            
            if os.path.exists(encoding_file):
                encoding = np.load(encoding_file)
                print(f"  Loaded shape: {encoding.shape}, dtype: {encoding.dtype}")
                filenames.append(entry['basename'])
                embeddings.append(encoding)
            else:
                missing_files.append(entry['encoding_file'])
        
        if missing_files:
            print(f"\n⚠️ {len(missing_files)} encoding files not found")
            print("First 5 missing files:")
            for mf in missing_files[:5]:
                print(f"  - {mf}")
        
        if not embeddings:
            print(f"\n❌ No valid encoding files found in {ENCODED_RESULT_DIR}")
            return None
        
        print(f"\n✅ Successfully loaded {len(embeddings)} encodings")
        print(f"EMBEDDING_DIM from CNN: {EMBEDDING_DIM}")
        
        # Stack into matrix
        matrix = np.stack(embeddings)
        print(f"Matrix shape: {matrix.shape}")
        
        gallery = CNNGallerySet(filenames=filenames, matrix=matrix)
        print(f"Gallery created with {len(gallery)} faces")
        
        return gallery
    
    except Exception as e:
        print(f"❌ Error loading encodings: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("Testing cache loading...")
    print("=" * 60)
    
    result = test_load_encodings()
    
    if result:
        print("\n" + "=" * 60)
        print("✅ SUCCESS: Cache loading works!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED: Cache loading failed")
        print("=" * 60)
