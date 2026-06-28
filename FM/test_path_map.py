"""Test script to verify path mapping works correctly."""

import os
import json
import numpy as np
from CNN import CNNGallerySet, EMBEDDING_DIM

ENCODED_RESULT_DIR = r"d:\Mini-Project\FM\encoded_result"

def test_path_mapping():
    """Test that path mapping correctly maps to original image files."""
    manifest_path = os.path.join(ENCODED_RESULT_DIR, "manifest.json")
    
    print(f"Manifest path: {manifest_path}")
    print(f"Manifest exists: {os.path.exists(manifest_path)}")
    
    if not os.path.exists(manifest_path):
        print("ERROR: Manifest file not found!")
        return False
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        print(f"SUCCESS: Loaded manifest with {len(manifest)} entries\n")
        
        # Load all encodings with path mapping
        filenames = []
        embeddings = []
        seen_basenames = {}
        path_map = {}
        
        for original_path, entry in manifest.items():
            encoding_file = os.path.join(ENCODED_RESULT_DIR, entry['encoding_file'])
            
            if os.path.exists(encoding_file):
                encoding = np.load(encoding_file)
                
                # Create unique filename
                basename = entry['basename']
                if basename in seen_basenames:
                    seen_basenames[basename] += 1
                    unique_name = f"{os.path.splitext(basename)[0]}_{seen_basenames[basename]}{os.path.splitext(basename)[1]}"
                else:
                    seen_basenames[basename] = 0
                    unique_name = basename
                
                filenames.append(unique_name)
                embeddings.append(encoding)
                path_map[unique_name] = entry['original_path']
        
        print(f"Loaded {len(filenames)} encodings\n")
        
        # Test first 10 mappings
        print("Testing first 10 path mappings:")
        print("=" * 80)
        
        for i, unique_name in enumerate(filenames[:10]):
            original_path = path_map[unique_name]
            exists = os.path.exists(original_path)
            status = "OK" if exists else "MISSING"
            
            print(f"{i+1}. {unique_name}")
            print(f"   -> {original_path}")
            print(f"   Status: {status}")
            print()
        
        # Check how many images exist
        existing_count = sum(1 for unique_name in filenames if os.path.exists(path_map[unique_name]))
        missing_count = len(filenames) - existing_count
        
        print("=" * 80)
        print(f"Summary:")
        print(f"  Total entries: {len(filenames)}")
        print(f"  Images exist: {existing_count}")
        print(f"  Images missing: {missing_count}")
        
        if missing_count > 0:
            print(f"\nWARNING: {missing_count} image files not found at their original paths!")
            return False
        
        print("\nSUCCESS: All images found at their original paths!")
        return True
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Path Mapping")
    print("=" * 80)
    print()
    
    result = test_path_mapping()
    
    print()
    print("=" * 80)
    if result:
        print("RESULT: Path mapping works correctly!")
    else:
        print("RESULT: Path mapping has issues")
    print("=" * 80)
